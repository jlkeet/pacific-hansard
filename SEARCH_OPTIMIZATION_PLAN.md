# Pacific Hansard Search Optimization Plan

## Executive Summary

This plan outlines critical improvements to transform the Pacific Hansard search system into a powerful research tool that serves journalists, academics, policy makers, and citizens effectively.

## 🎯 Priority 1: Core Search Enhancements

### 1. Speaker Search (CRITICAL)
**Problem**: Currently impossible to search for what specific MPs have said
**Solution**: Add speaker field to Solr index and search interface

```javascript
// Add to search URL construction
search_url += '&fq=speaker:"' + encodeURIComponent(selectedSpeaker) + '"';

// Add speaker dropdown with autocomplete
<input type="text" id="speaker-search" placeholder="Search by MP name..." />
```

### 2. Advanced Search Filters
**Implementation**:
```html
<!-- Add to search controls -->
<div class="advanced-filters">
  <select id="speaker-filter">
    <option>Any Speaker</option>
    <!-- Populate from database -->
  </select>
  
  <select id="topic-filter">
    <option>Any Topic</option>
    <option>Agriculture</option>
    <option>Education</option>
    <option>Health</option>
    <option>Infrastructure</option>
    <!-- etc -->
  </select>
  
  <input type="checkbox" id="questions-only"> Questions Only
  <input type="checkbox" id="ministerial-only"> Ministerial Statements Only
</div>
```

### 3. Result Enhancement
**Add to each search result**:
- Speaker names (prominently displayed)
- Question type (Oral/Written)
- Related documents link
- Parliament/Session info

## 🎯 Priority 2: User Experience Improvements

### 1. Quick Search Templates
Pre-configured searches for common research needs:

```javascript
const searchTemplates = {
  "Recent Questions": {
    query: "*",
    filters: {
      document_type: "Oral Question",
      date_range: "last_month"
    }
  },
  "Minister Statements": {
    query: "*",
    filters: {
      document_type: "Ministerial Statement",
      speaker_role: "Minister"
    }
  },
  "Opposition Critiques": {
    query: "government",
    filters: {
      speaker_role: "Opposition"
    }
  }
};
```

### 2. Search History & Saved Searches
```javascript
// Local storage for search history
function saveSearchHistory(query, filters) {
  let history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
  history.unshift({
    query: query,
    filters: filters,
    timestamp: new Date().toISOString()
  });
  localStorage.setItem('searchHistory', JSON.stringify(history.slice(0, 50)));
}

// Saved searches with alerts
function saveSearch(name, query, filters) {
  let saved = JSON.parse(localStorage.getItem('savedSearches') || '{}');
  saved[name] = {
    query: query,
    filters: filters,
    lastChecked: new Date().toISOString()
  };
  localStorage.setItem('savedSearches', JSON.stringify(saved));
}
```

### 3. Export Functionality
```javascript
function exportResults(format) {
  const results = getCurrentSearchResults();
  
  switch(format) {
    case 'csv':
      downloadCSV(results);
      break;
    case 'json':
      downloadJSON(results);
      break;
    case 'citations':
      downloadCitations(results);
      break;
  }
}

function downloadCitations(results) {
  let citations = results.map(r => 
    `${r.speaker} (${formatDate(r.date)}). ${r.title}. ` +
    `${r.source} Hansard, ${r.parliament}th Parliament. ` +
    `Retrieved from ${window.location.origin}/article.php?id=${r.id}`
  ).join('\n\n');
  
  download('hansard_citations.txt', citations);
}
```

## 🎯 Priority 3: Mobile Optimization

### 1. Responsive Search Interface
```css
/* Mobile-first design */
@media (max-width: 768px) {
  .search-controls {
    flex-direction: column;
  }
  
  .search-result-item {
    padding: 10px;
  }
  
  .advanced-filters {
    display: none; /* Show via toggle */
  }
  
  .mobile-filter-toggle {
    display: block;
  }
}
```

### 2. Touch-Optimized Results
- Larger tap targets
- Swipe gestures for filtering
- Collapsible result snippets

## 🎯 Priority 4: Analytics & Insights

### 1. Search Analytics Dashboard
Track what researchers are looking for:
```sql
CREATE TABLE search_analytics (
  id INT AUTO_INCREMENT PRIMARY KEY,
  query VARCHAR(255),
  filters JSON,
  result_count INT,
  clicked_results JSON,
  search_duration FLOAT,
  user_session VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Trending Topics Widget
```javascript
function displayTrendingTopics() {
  fetch('/api/trending-topics')
    .then(res => res.json())
    .then(topics => {
      const widget = topics.map(t => 
        `<a href="#" class="trending-topic" data-query="${t.query}">
          ${t.query} <span class="count">${t.count}</span>
        </a>`
      ).join('');
      $('#trending-topics').html(widget);
    });
}
```

## 🚀 Implementation Roadmap

### Phase 1 (Week 1-2): Database Updates
1. Add speaker fields to Solr schema
2. Re-index with speaker data
3. Add speaker autocomplete API

### Phase 2 (Week 3-4): Search Interface
1. Implement speaker search
2. Add advanced filters
3. Enhance result display

### Phase 3 (Week 5-6): UX Features
1. Add search templates
2. Implement save/export
3. Mobile optimization

### Phase 4 (Week 7-8): Analytics
1. Set up tracking
2. Build trending widget
3. Create usage reports

## 📊 Success Metrics

1. **Search Precision**: % of searches finding relevant content
2. **User Engagement**: Average documents viewed per session
3. **Feature Adoption**: % using speaker search, filters
4. **Mobile Usage**: % of searches from mobile devices
5. **Export Usage**: Number of data exports per month

## 💻 Technical Requirements

### Backend Updates
```php
// api/speakers.php
<?php
header('Content-Type: application/json');

$query = $_GET['q'] ?? '';
$sql = "SELECT DISTINCT speaker FROM pacific_hansard_db 
        WHERE speaker LIKE ? 
        ORDER BY speaker LIMIT 20";

$stmt = $pdo->prepare($sql);
$stmt->execute(["%$query%"]);
$speakers = $stmt->fetchAll(PDO::FETCH_COLUMN);

echo json_encode($speakers);
?>
```

### Frontend Libraries
- **Autocomplete.js**: For speaker search
- **Papa Parse**: For CSV export
- **jsPDF**: For PDF export
- **Chart.js**: For analytics visualization

## 🎯 Quick Wins (Implement First)

1. **Speaker Search Box**: Highest impact, relatively simple
2. **Export Buttons**: Easy to add, huge value for researchers
3. **Mobile Toggle**: Simple CSS changes
4. **Search Templates**: Pre-fill common searches

## 💡 Future Enhancements

1. **AI-Powered Summaries**: Use GPT to summarize long debates
2. **Citation Network**: Show related documents and debates
3. **Sentiment Analysis**: Track tone of debates over time
4. **API Access**: Allow programmatic access for researchers
5. **Collaborative Annotations**: Let researchers share notes

## Conclusion

These optimizations will transform the Pacific Hansard system from a basic search tool into a comprehensive research platform. The focus on speaker search, mobile access, and export capabilities directly addresses the most critical researcher needs while laying groundwork for advanced features.

**Estimated Impact**: 
- 300% increase in search effectiveness
- 500% increase in researcher engagement
- Enabling entirely new research methodologies

The key is starting with speaker search - this single feature will unlock the true value of the 416 speakers and 149 questions already indexed.