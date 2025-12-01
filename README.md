# Szuru App

Simple web application for some utility tasks in Szuruboru. An example compose file is provided to get you started.

## Media import

1. Uses `gallery-dl` to download media + metadata from a supplied URL.
2. Extracts metadata.
3. Ensures categories and tags exist in Szurubooru, then uploads the media.

## Tags

Adding implications in Szurubooru won't add the implied tag(s) where they ought to be present on existing items. There is a page that will let you fix this for either a selection of tags or globally scan and fix this everywhere.

## Container (local build)

```powershell
docker build -t szuru-webtools:dev .
docker run --rm -p 8000:8000 `
  -e SZURU_BASE=$env:SZURU_BASE `
  -e SZURU_USER=$env:SZURU_USER `
  -e SZURU_TOKEN=$env:SZURU_TOKEN `
  szuru-webtools:dev
```

## Web Interface

Open <http://localhost:8000> in your browser to access:

- **Import Media** (`/`): Download and import media from URLs
- **Tag Tools** (`/tag-tools`): Bulk tag operations

Environment variables (prefix `SZURU_`):

- `SZURU_BASE` (Base URL) e.g. <https://szurubooru.your.domain>
- `SZURU_USER`
- `SZURU_PASSWORD` (if using password auth)
- `SZURU_TOKEN` (if using token auth)

## Notes

I vibe-coded this to address some personal pain-points. This is not my area of expertise. Use at your own risk.

That said, PRs are welcome if you have improvements or fixes.
