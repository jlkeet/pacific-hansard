// Enhanced Pacific Hansard Search
$(document).ready(function() {
    // Global variables
    let currentQuery = '';
    let currentFilters = {};
    let selectedSpeaker = '';
    let searchResults = [];
    let start = 0;
    
    // Initialize
    initializeSpeakerAutocomplete();
    bindEventHandlers();
    loadSearchHistory();
    
    // Perform initial search if there's a query
    if ($('#search-query').val()) {
        performSearch();
    }
    
    // Speaker Autocomplete
    function initializeSpeakerAutocomplete() {
        $('#speaker-search').autoComplete({
            source: function(term, response) {
                $.getJSON('/api/speakers.php', { q: term }, function(data) {
                    response(data.speakers);
                });
            },
            minChars: 2,
            delay: 150,
            onSelect: function(e, term, item) {
                selectedSpeaker = term;
                performSearch();
            }
        });
    }
    
    // Search Templates
    const searchTemplates = {
        'recent-questions': {
            query: '*',
            filters: {
                document_type: 'Oral Question',
                date_range: 'month'
            },
            description: 'Recent parliamentary questions'
        },
        'ministerial': {
            query: 'minister',
            filters: {
                document_type: 'Hansard Document'
            },
            description: 'Ministerial statements'
        },
        'today-in-history': {
            query: '*',
            filters: {
                date_range: 'today-historical'
            },
            description: 'What happened on this day in previous years'
        },
        'my-mp': {
            query: '',
            filters: {},
            showSpeakerSearch: true,
            description: 'Search by MP name'
        }
    };
    
    // Bind Event Handlers
    function bindEventHandlers() {
        // Search form
        $('#search-form').on('submit', function(e) {
            e.preventDefault();
            performSearch();
        });
        
        // Template buttons
        $('.template-btn').on('click', function() {
            const templateKey = $(this).data('template');
            applySearchTemplate(templateKey);
        });
        
        // Filters
        $('#date-filter, #source-filter, #type-filter').on('change', performSearch);
        $('#questions-only, #answers-only, #recent-first').on('change', performSearch);
        
        // Mobile filter toggle
        $('#mobile-filter-btn').on('click', function() {
            $('#advanced-filters').toggle();
            $(this).html(
                $('#advanced-filters').is(':visible') 
                    ? '<i class="fa fa-filter"></i> Hide Filters' 
                    : '<i class="fa fa-filter"></i> Show Filters'
            );
        });
        
        // Custom date range
        $('#date-filter').on('change', function() {
            if ($(this).val() === 'custom') {
                $('#customDateModal').modal('show');
            }
        });
        
        $('#applyCustomDateRange').on('click', function() {
            const startDate = $('#customStartDate').val();
            const endDate = $('#customEndDate').val();
            
            if (startDate && endDate) {
                currentFilters.customDateRange = {
                    start: startDate,
                    end: endDate
                };
                $('#customDateModal').modal('hide');
                performSearch();
            }
        });
        
        // Clear speaker search
        $('#speaker-search').on('input', function() {
            if ($(this).val() === '') {
                selectedSpeaker = '';
                performSearch();
            }
        });
        
        // Infinite scroll
        $(window).scroll(function() {
            if ($(document).height() - $(window).height() === $(window).scrollTop()) {
                loadMoreResults();
            }
        });
    }
    
    // Apply search template
    function applySearchTemplate(templateKey) {
        const template = searchTemplates[templateKey];
        if (!template) return;
        
        // Set query
        $('#search-query').val(template.query);
        
        // Apply filters
        if (template.filters.document_type) {
            $('#type-filter').val(template.filters.document_type);
        }
        if (template.filters.date_range) {
            $('#date-filter').val(template.filters.date_range);
        }
        
        // Focus speaker search if needed
        if (template.showSpeakerSearch) {
            $('#speaker-search').focus();
        }
        
        // Perform search
        performSearch();
    }
    
    // Main search function
    function performSearch(append = false) {
        if (!append) {
            start = 0;
            searchResults = [];
            $('.search-result-list').empty();
        }
        
        currentQuery = $('#search-query').val() || '*';
        
        // Build filters
        currentFilters = {
            speaker: selectedSpeaker,
            document_type: $('#type-filter').val(),
            source: $('#source-filter').val(),
            date_range: $('#date-filter').val(),
            questions_only: $('#questions-only').is(':checked'),
            answers_only: $('#answers-only').is(':checked')
        };
        
        // Save to history
        saveSearchHistory(currentQuery, currentFilters);
        
        // Show loading
        $('.loading').show();
        showLoadingOverlay();
        
        // Build Solr query
        const searchUrl = buildSolrQuery(currentQuery, currentFilters, start);
        
        // Execute search
        console.log('Searching with URL:', searchUrl);
        $.get(searchUrl, function(data) {
            console.log('Search response:', data);
            hideLoadingOverlay();
            $('.loading').hide();
            
            if (data.response && data.response.docs) {
                displayResults(data, append);
                updateExportButtons(data.response.numFound);
            } else {
                console.error('No response data:', data);
                showError('No results found.');
            }
        }).fail(function(xhr, status, error) {
            console.error('Search failed:', status, error);
            console.error('Response:', xhr.responseText);
            hideLoadingOverlay();
            $('.loading').hide();
            showError('Search failed: ' + error);
        });
    }
    
    // Build Solr query URL
    function buildSolrQuery(query, filters, start) {
        let url = '/solr/hansard_core/select?';
        // Use proper query syntax with operator
        url += 'q={!q.op=AND df=content}' + encodeURIComponent(query);
        url += '&fl=id,title,date,source,speaker,speaker2,content,document_type,new_id';
        url += '&hl=true&hl.fl=content&hl.snippets=3&hl.fragsize=250';
        url += '&rows=20&start=' + start;
        url += '&wt=json';
        url += '&facet=true&facet.mincount=1&facet.field=source&facet.field=document_type&facet.field=speaker&facet.field=speaker2';
        
        // Add filters
        const fq = [];
        
        if (filters.speaker) {
            fq.push('(speaker:"' + filters.speaker + '" OR speaker2:"' + filters.speaker + '")');
        }
        
        if (filters.document_type) {
            fq.push('document_type:"' + filters.document_type + '"');
        }
        
        if (filters.source) {
            fq.push('source:"' + filters.source + '"');
        }
        
        if (filters.questions_only) {
            fq.push('(document_type:"Oral Question" OR document_type:"Written Question")');
        }
        
        // Date range filter
        if (filters.date_range) {
            const dateFilter = buildDateRangeFilter(filters.date_range);
            if (dateFilter) fq.push(dateFilter);
        }
        
        // Add filter queries
        fq.forEach(filter => {
            url += '&fq=' + encodeURIComponent(filter);
        });
        
        // Sort
        if ($('#recent-first').is(':checked')) {
            url += '&sort=date desc';
        }
        
        return url;
    }
    
    // Build date range filter
    function buildDateRangeFilter(range) {
        const now = new Date();
        let start, end;
        
        switch(range) {
            case 'day':
                start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                break;
            case 'week':
                start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                break;
            case 'month':
                start = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
                break;
            case 'year':
                start = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
                break;
            case 'custom':
                if (currentFilters.customDateRange) {
                    return `date:[${currentFilters.customDateRange.start}T00:00:00Z TO ${currentFilters.customDateRange.end}T23:59:59Z]`;
                }
                return null;
            default:
                return null;
        }
        
        if (start) {
            return `date:[${start.toISOString()} TO NOW]`;
        }
        return null;
    }
    
    // Display search results
    function displayResults(data, append) {
        const results = data.response.docs;
        const highlighting = data.highlighting || {};
        
        // Update summary
        if (!append) {
            $('.search-summary').html(
                `Found <strong>${data.response.numFound}</strong> results` +
                (currentFilters.speaker ? ` for speaker "<strong>${currentFilters.speaker}</strong>"` : '') +
                (currentQuery !== '*:*' ? ` matching "<strong>${currentQuery}</strong>"` : '')
            );
        }
        
        // Add results
        results.forEach((doc, index) => {
            searchResults.push(doc);
            const resultHtml = createResultItem(doc, highlighting[doc.id], start + index);
            $('.search-result-list').append(resultHtml);
        });
        
        // Show/hide export buttons
        if (data.response.numFound > 0) {
            $('.export-buttons').show();
        }
    }
    
    // Create result item HTML
    function createResultItem(doc, highlighting, index) {
        let html = '<div class="search-result-item">';
        
        // Title with badges
        html += '<h4 class="search-result-title">' + doc.title;
        
        // Speaker badges
        if (doc.speaker) {
            html += ' <span class="speaker-badge">' + doc.speaker + '</span>';
        }
        if (doc.speaker2) {
            html += ' <span class="speaker-badge">' + doc.speaker2 + '</span>';
        }
        
        // Document type badge
        if (doc.document_type === 'Oral Question' || doc.document_type === 'Written Question') {
            html += ' <span class="question-type-badge">' + doc.document_type + '</span>';
        }
        
        html += '</h4>';
        
        // Date and source
        html += '<p class="search-result-attribution">';
        html += '<i class="fa fa-calendar"></i> ' + formatDate(doc.date) + ' ';
        html += '<span class="badge badge-warning">' + doc.source + '</span>';
        html += '</p>';
        
        // Snippet
        if (highlighting && highlighting.content) {
            html += '<div class="search-result-snippet">';
            highlighting.content.forEach(snippet => {
                html += '<p>...' + snippet + '...</p>';
            });
            html += '</div>';
        } else if (doc.content) {
            // Handle content as array or string
            const content = Array.isArray(doc.content) ? doc.content[0] : doc.content;
            html += '<p class="search-result-snippet">' + 
                    content.substring(0, 200) + '...</p>';
        }
        
        // Actions
        html += '<div class="search-result-actions">';
        html += '<a href="article.php?id=' + doc.new_id + 
                '" class="btn btn-primary btn-sm" target="_blank">View Full Text</a>';
        html += '</div>';
        
        html += '</div>';
        return html;
    }
    
    // Export functionality
    window.exportResults = function(format) {
        if (searchResults.length === 0) {
            alert('No results to export');
            return;
        }
        
        switch(format) {
            case 'csv':
                exportCSV();
                break;
            case 'json':
                exportJSON();
                break;
            case 'citations':
                exportCitations();
                break;
        }
    };
    
    function exportCSV() {
        let csv = 'Title,Date,Source,Speaker,Speaker2,Document Type,URL\n';
        
        searchResults.forEach(doc => {
            csv += '"' + (doc.title || '').replace(/"/g, '""') + '",';
            csv += '"' + formatDate(doc.date) + '",';
            csv += '"' + (doc.source || '') + '",';
            csv += '"' + (doc.speaker || '') + '",';
            csv += '"' + (doc.speaker2 || '') + '",';
            csv += '"' + (doc.document_type || '') + '",';
            csv += '"' + window.location.origin + '/article.php?id=' + doc.new_id + '"\n';
        });
        
        downloadFile('hansard_results.csv', csv, 'text/csv');
    }
    
    function exportJSON() {
        const data = {
            query: currentQuery,
            filters: currentFilters,
            results: searchResults,
            exportDate: new Date().toISOString()
        };
        
        downloadFile('hansard_results.json', JSON.stringify(data, null, 2), 'application/json');
    }
    
    function exportCitations() {
        let citations = 'Pacific Hansard Search Results\n';
        citations += 'Exported: ' + new Date().toLocaleString() + '\n\n';
        
        searchResults.forEach((doc, index) => {
            citations += `[${index + 1}] `;
            if (doc.speaker) citations += doc.speaker + '. ';
            citations += `(${formatDate(doc.date)}). `;
            citations += doc.title + '. ';
            citations += doc.source + ' Hansard. ';
            citations += `Retrieved from ${window.location.origin}/article.php?id=${doc.new_id}`;
            citations += '\n\n';
        });
        
        downloadFile('hansard_citations.txt', citations, 'text/plain');
    }
    
    // Utility functions
    function downloadFile(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    function formatDate(dateString) {
        if (!dateString) return 'Unknown date';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    }
    
    function showLoadingOverlay() {
        $('.loading-overlay').css('display', 'flex');
    }
    
    function hideLoadingOverlay() {
        $('.loading-overlay').hide();
    }
    
    function showError(message) {
        $('.search-result-list').html(
            '<div class="alert alert-danger">' + message + '</div>'
        );
    }
    
    // Search history
    function saveSearchHistory(query, filters) {
        let history = JSON.parse(localStorage.getItem('hansardSearchHistory') || '[]');
        history.unshift({
            query: query,
            filters: filters,
            timestamp: new Date().toISOString()
        });
        // Keep only last 50 searches
        history = history.slice(0, 50);
        localStorage.setItem('hansardSearchHistory', JSON.stringify(history));
    }
    
    function loadSearchHistory() {
        const history = JSON.parse(localStorage.getItem('hansardSearchHistory') || '[]');
        // Could display recent searches in UI
    }
    
    // Load more results
    function loadMoreResults() {
        if ($('.loading').is(':visible')) return;
        start += 20;
        performSearch(true);
    }
    
    // Update export buttons
    function updateExportButtons(numFound) {
        if (numFound > searchResults.length) {
            $('.export-buttons').append(
                '<button class="btn btn-sm btn-outline-warning" onclick="exportAllResults()">' +
                '<i class="fa fa-download"></i> Export All ' + numFound + ' Results</button>'
            );
        }
    }
    
    // Export all results (not just loaded ones)
    window.exportAllResults = function() {
        alert('Full export functionality would fetch all results. Currently showing first ' + 
              searchResults.length + ' results.');
        // In production, this would make multiple API calls to get all results
    };
});