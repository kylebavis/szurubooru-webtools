class ApiClient {
  static async request(endpoint, options = {}) {
    const url = `/api${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }

      return data;
    } catch (error) {
      if (error instanceof TypeError) {
        throw new Error('Network error - check your connection');
      }
      throw error;
    }
  }

  static async importMedia(url, safety = 'safe') {
    return this.request('/import', {
      method: 'POST',
      body: JSON.stringify({ url, safety })
    });
  }

  static async applyImplications(tags, dryRun = false, fullScan = false) {
    return this.request('/tag-tools/apply-implications', {
      method: 'POST',
      body: JSON.stringify({ tags, dry_run: dryRun, full_scan: fullScan })
    });
  }
}

class UI {
  static showLoading(button) {
    button.disabled = true;
    button.innerHTML = '<span class="loading"></span>Processing...';
  }

  static hideLoading(button, text = 'Submit') {
    button.disabled = false;
    button.innerHTML = text;
  }

  static showResult(elementId, data, type = 'info') {
    const element = document.getElementById(elementId);
    element.className = `result ${type}`;
    element.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    element.scrollTop = 0;
  }

  static formatImplicationResult(data) {
    const stats = document.createElement('div');
    stats.className = 'stats';
    stats.innerHTML = `
      <div class="stat-box">
        <div class="stat-number">${data.original_count}</div>
        <div class="stat-label">Original Tags</div>
      </div>
      <div class="stat-box">
        <div class="stat-number">${data.added.length}</div>
        <div class="stat-label">Added Implications</div>
      </div>
      <div class="stat-box">
        <div class="stat-number">${data.total}</div>
        <div class="stat-label">Total Tags</div>
      </div>
    `;

    const tagList = document.createElement('div');
    if (data.added.length > 0) {
      tagList.innerHTML = '<h3>Added Implications:</h3>';
      const tags = document.createElement('div');
      tags.className = 'tag-list';
      tags.innerHTML = data.added.map(tag => `<span class="tag new">${tag}</span>`).join('');
      tagList.appendChild(tags);
    } else {
      tagList.innerHTML = '<p>No additional implications found.</p>';
    }

    return [stats, tagList];
  }
}

// Set active nav link
function setActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll('nav a').forEach(link => {
    link.classList.remove('active');
    if (link.getAttribute('href') === path) {
      link.classList.add('active');
    }
  });
}

// Initialize on load
document.addEventListener('DOMContentLoaded', setActiveNav);
