import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.downloader import collect_source_for_file, collect_tags_for_file, run_gallery_dl
from app.services.szuru_client import szuru_client
from app.services.tag_logic import tags_for_upload

router = APIRouter()

class ImportRequest(BaseModel):
    url: str
    safety: str = 'safe'

class FetchResponse(BaseModel):
    downloaded: int
    uploaded: int
    errors: int
    details: list[str]

class ApplyImplicationsRequest(BaseModel):
    tags: list[str]
    dry_run: bool = False
    full_scan: bool = False

class ApplyImplicationsResponse(BaseModel):
    processed_tags: int
    posts_found: int
    posts_updated: int
    implications_added: int
    details: list[str]

class DeleteUnusedTagsRequest(BaseModel):
    dry_run: bool = False

class DeleteUnusedTagsResponse(BaseModel):
    tags_found: int
    tags_deleted: int
    details: list[str]

@router.post('/import', response_model=FetchResponse)
async def import_media(req: ImportRequest):
    try:
        dl = await run_gallery_dl(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    uploaded = 0
    errors = 0
    details: list[str] = []
    for file in dl.files:
        # infer tags and source
        raw_tags = collect_tags_for_file(file)
        source_url = collect_source_for_file(file)
        categories, upload_tags = tags_for_upload(raw_tags)
        # ensure categories + tags
        order = 0
        for cat in sorted(categories.keys()):
            await szuru_client.ensure_category(cat, order=order)
            order += 1
            for tag in sorted(categories[cat]):
                await szuru_client.ensure_tag(tag, cat)
        try:
            await szuru_client.upload_post(str(file), upload_tags, safety=req.safety, source=source_url)
            uploaded += 1
        except Exception as e:
            errors += 1
            details.append(f"Upload failed {file.name}: {e}")
        finally:
            # Move the media file and any metadata sidecars to a processed directory
            try:
                processed_dir = dl.base_dir / 'processed'
                processed_dir.mkdir(parents=True, exist_ok=True)
                # move the main file
                target = processed_dir / file.name
                file.replace(target)
                # move sidecars if present
                for suf in ('.json', '.info.json'):
                    side = file.with_name(file.name + suf)
                    if side.exists():
                        side.replace(processed_dir / side.name)
            except Exception as e:
                # record move errors but don't stop processing
                details.append(f"Failed to move {file.name} to processed: {e}")
    return FetchResponse(downloaded=len(dl.files), uploaded=uploaded, errors=errors, details=details)

@router.post('/tag-tools/apply-implications', response_model=ApplyImplicationsResponse)
async def apply_implications_to_posts(req: ApplyImplicationsRequest):
    from app.services.tag_logic import normalize_tag

    processed_tags = 0
    total_posts_found = 0
    total_posts_updated = 0
    total_implications_added = 0
    details = []

    # Determine which tags to process
    if req.full_scan:
        details.append("Full scan mode: Getting all tags with implications...")
        try:
            tags_to_process = await szuru_client.get_all_tags_with_implications()
            details.append(f"Found {len(tags_to_process)} tags with implications")
        except Exception as e:
            details.append(f"Error getting tags with implications: {e}")
            tags_to_process = []
    else:
        tags_to_process = req.tags

    for tag in tags_to_process:
        normalized_tag = normalize_tag(tag)
        if not normalized_tag:
            continue

        processed_tags += 1

        try:
            # Get implications for this tag
            implications = await szuru_client.get_implications(normalized_tag)
            if not implications:
                details.append(f"No implications found for tag: {normalized_tag}")
                continue

            details.append(f"Tag '{normalized_tag}' implies: {', '.join(implications)}")

            # Search for posts with this tag - use pagination to get all posts
            all_posts = []
            offset = 0
            limit = 100  # Szurubooru's maximum limit

            while True:
                search_result = await szuru_client.search_posts(f"tag:{normalized_tag}", limit=limit, offset=offset)
                posts = search_result.get('results', [])

                if not posts:
                    break

                all_posts.extend(posts)

                # If we got fewer results than the limit, we've reached the end
                if len(posts) < limit:
                    break

                offset += limit

            posts_found = len(all_posts)
            total_posts_found += posts_found

            if posts_found == 0:
                details.append(f"No posts found with tag: {normalized_tag}")
                continue

            details.append(f"Found {posts_found} posts with tag: {normalized_tag}")

            posts_updated_for_tag = 0
            implications_added_for_tag = 0

            for post in all_posts:
                post_id = post.get('id')
                post_version = post.get('version')
                current_tags = [t.get('names', [None])[0] for t in post.get('tags', []) if t.get('names')]
                current_tags = [t for t in current_tags if t]  # Remove None values

                # Check which implications are missing
                missing_implications = [imp for imp in implications if imp not in current_tags]

                if missing_implications:
                    if not req.dry_run:
                        # Add missing implications to current tags
                        new_tags = current_tags + missing_implications
                        try:
                            await szuru_client.update_post_tags(post_id, new_tags, post_version)
                            posts_updated_for_tag += 1
                            implications_added_for_tag += len(missing_implications)
                            details.append(f"Post {post_id}: Added {', '.join(missing_implications)}")
                            print(f"DEBUG: Updated post {post_id}, total updated for tag: {posts_updated_for_tag}")
                        except Exception as e:
                            details.append(f"Failed to update post {post_id}: {e}")
                    else:
                        details.append(f"Post {post_id}: Would add {', '.join(missing_implications)}")
                        implications_added_for_tag += len(missing_implications)

            total_posts_updated += posts_updated_for_tag
            total_implications_added += implications_added_for_tag

            if req.dry_run:
                details.append(f"DRY RUN: Would update {len([p for p in all_posts if any(imp not in [t.get('names', [None])[0] for t in p.get('tags', [])] for imp in implications)])} posts for tag '{normalized_tag}'")
            else:
                details.append(f"Updated {posts_updated_for_tag} posts for tag '{normalized_tag}'")

        except Exception as e:
            details.append(f"Error processing tag '{normalized_tag}': {e}")

    return ApplyImplicationsResponse(
        processed_tags=processed_tags,
        posts_found=total_posts_found,
        posts_updated=total_posts_updated,
        implications_added=total_implications_added,
        details=details
    )

@router.post('/tag-tools/apply-implications-stream')
async def apply_implications_stream(req: ApplyImplicationsRequest):
    """Streaming version that provides real-time progress updates"""

    async def generate_updates():
        from app.services.tag_logic import normalize_tag

        processed_tags = 0
        total_posts_found = 0
        total_posts_updated = 0
        total_implications_added = 0

        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting tag implication process...'})}\n\n"

            # Determine which tags to process
            if req.full_scan:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Full scan mode: Getting all tags with implications...'})}\n\n"
                try:
                    tags_to_process = await szuru_client.get_all_tags_with_implications()
                    yield f"data: {json.dumps({'type': 'status', 'message': f'Found {len(tags_to_process)} tags with implications'})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Error getting tags with implications: {e}'})}\n\n"
                    return
            else:
                tags_to_process = req.tags

            total_tags = len(tags_to_process)

            for tag_index, tag in enumerate(tags_to_process):
                normalized_tag = normalize_tag(tag)
                if not normalized_tag:
                    continue

                processed_tags += 1

                yield f"data: {json.dumps({'type': 'progress', 'current': tag_index + 1, 'total': total_tags, 'tag': normalized_tag})}\n\n"

                try:
                    # Get implications for this tag
                    implications = await szuru_client.get_implications(normalized_tag)
                    if not implications:
                        yield f"data: {json.dumps({'type': 'info', 'message': f'No implications found for tag: {normalized_tag}'})}\n\n"
                        continue

                    implications_str = ', '.join(implications)
                    yield f"data: {json.dumps({'type': 'info', 'message': f'Tag {normalized_tag} implies: {implications_str}'})}\n\n"

                    # Search for posts with this tag - use pagination
                    all_posts = []
                    offset = 0
                    limit = 100

                    while True:
                        search_result = await szuru_client.search_posts(f"tag:{normalized_tag}", limit=limit, offset=offset)
                        posts = search_result.get('results', [])

                        if not posts:
                            break

                        all_posts.extend(posts)

                        if len(posts) < limit:
                            break

                        offset += limit

                    posts_found = len(all_posts)
                    total_posts_found += posts_found

                    if posts_found == 0:
                        yield f"data: {json.dumps({'type': 'info', 'message': f'No posts found with tag: {normalized_tag}'})}\n\n"
                        continue

                    yield f"data: {json.dumps({'type': 'info', 'message': f'Found {posts_found} posts with tag: {normalized_tag}'})}\n\n"

                    posts_updated_for_tag = 0
                    implications_added_for_tag = 0

                    for post in all_posts:
                        post_id = post.get('id')
                        post_version = post.get('version')
                        current_tags = [t.get('names', [None])[0] for t in post.get('tags', []) if t.get('names')]
                        current_tags = [t for t in current_tags if t]

                        # Check which implications are missing
                        missing_implications = [imp for imp in implications if imp not in current_tags]

                        if missing_implications:
                            if not req.dry_run:
                                # Add missing implications to current tags
                                new_tags = current_tags + missing_implications
                                try:
                                    await szuru_client.update_post_tags(post_id, new_tags, post_version)
                                    posts_updated_for_tag += 1
                                    implications_added_for_tag += len(missing_implications)
                                    added_tags = ', '.join(missing_implications)
                                    yield f"data: {json.dumps({'type': 'success', 'message': f'Post {post_id}: Added {added_tags}'})}\n\n"
                                except Exception as e:
                                    yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to update post {post_id}: {e}'})}\n\n"
                            else:
                                would_add_tags = ', '.join(missing_implications)
                                yield f"data: {json.dumps({'type': 'info', 'message': f'Post {post_id}: Would add {would_add_tags}'})}\n\n"
                                implications_added_for_tag += len(missing_implications)

                    total_posts_updated += posts_updated_for_tag
                    total_implications_added += implications_added_for_tag

                    if req.dry_run:
                        summary_msg = f'DRY RUN: Would update {posts_updated_for_tag} posts for tag {normalized_tag}'
                        yield f"data: {json.dumps({'type': 'summary', 'message': summary_msg})}\n\n"
                    else:
                        summary_msg = f'Updated {posts_updated_for_tag} posts for tag {normalized_tag}'
                        yield f"data: {json.dumps({'type': 'summary', 'message': summary_msg})}\n\n"

                except Exception as e:
                    error_msg = f'Error processing tag {normalized_tag}: {e}'
                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

            # Send final results
            final_message = "DRY RUN COMPLETE" if req.dry_run else "APPLICATION COMPLETE"
            if req.full_scan:
                final_message += " (FULL SCAN)"

            yield f"data: {json.dumps({'type': 'complete', 'data': {'processed_tags': processed_tags, 'posts_found': total_posts_found, 'posts_updated': total_posts_updated, 'implications_added': total_implications_added}, 'message': final_message})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Unexpected error: {e}'})}\n\n"

    return StreamingResponse(
        generate_updates(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.post('/tag-tools/delete-unused-tags-stream')
async def delete_unused_tags_stream(req: DeleteUnusedTagsRequest):
    """Streaming version that provides real-time progress updates for deleting unused tags"""

    async def generate_updates():
        tags_found = 0
        tags_deleted = 0

        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Finding tags with 0 usages...'})}\n\n"

            # Get all unused tags
            try:
                unused_tags = await szuru_client.get_unused_tags()
                tags_found = len(unused_tags)
                yield f"data: {json.dumps({'type': 'status', 'message': f'Found {tags_found} unused tags'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error getting unused tags: {e}'})}\n\n"
                return

            if tags_found == 0:
                yield f"data: {json.dumps({'type': 'info', 'message': 'No unused tags found'})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'data': {'tags_found': 0, 'tags_deleted': 0}, 'message': 'COMPLETE - No tags to delete'})}\n\n"
                return

            # Process each unused tag
            for tag_index, tag_data in enumerate(unused_tags):
                tag_names = tag_data.get('names', [])
                if not tag_names:
                    continue

                primary_name = tag_names[0]
                tag_version = tag_data.get('version')

                yield f"data: {json.dumps({'type': 'progress', 'current': tag_index + 1, 'total': tags_found, 'tag': primary_name})}\n\n"

                if not req.dry_run:
                    try:
                        await szuru_client.delete_tag(primary_name, tag_version)
                        tags_deleted += 1
                        yield f"data: {json.dumps({'type': 'success', 'message': f'Deleted tag: {primary_name}'})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to delete tag {primary_name}: {e}'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'info', 'message': f'Would delete tag: {primary_name}'})}\n\n"
                    tags_deleted += 1

            # Send final results
            final_message = f"DRY RUN COMPLETE - Would delete {tags_deleted} tags" if req.dry_run else f"DELETION COMPLETE - Deleted {tags_deleted} tags"
            yield f"data: {json.dumps({'type': 'complete', 'data': {'tags_found': tags_found, 'tags_deleted': tags_deleted}, 'message': final_message})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Unexpected error: {e}'})}\n\n"

    return StreamingResponse(
        generate_updates(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

