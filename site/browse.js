document.addEventListener('DOMContentLoaded', function() {
    loadCountries();
});

function loadCountries() {
    fetch('http://localhost:8080/api/countries.php')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('country-select');
            select.innerHTML = '<option value="">Select a Country</option>';
            data.forEach(country => {
                const option = document.createElement('option');
                option.value = country.source;
                option.textContent = country.source;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error loading countries:', error));
}

document.getElementById('country-select').addEventListener('change', function() {
    if (this.value) {
        loadHansardList(this.value);
    }
});

function loadHansardList(source) {
    fetch(`/api/hansard-list.php?source=${encodeURIComponent(source)}`)
        .then(response => response.json())
        .then(data => {
            console.log("Parsed data:", data);
            if (!Array.isArray(data)) {
                if (data.error) {
                    throw new Error(data.error);
                }
                throw new Error("Unexpected data format");
            }
            const list = document.getElementById('hansard-list');
            list.innerHTML = '';
            data.forEach((day, index) => {
                const dayElement = document.createElement('div');
                dayElement.className = 'day-group';
                dayElement.innerHTML = `
                    <h3 class="day-title" data-toggle="collapse" data-target="#day-${index}">
                        <span><i class="fas fa-calendar-alt mr-2"></i>${day.sitting_date}</span>
                        <span class="badge badge-light">${day.documents.length}</span>
                    </h3>
                    <div id="day-${index}" class="collapse">
                        ${day.documents.map(doc => `
                            <div class="document-item">
                                <h4 data-toggle="collapse" data-target="#doc-${doc.new_id}">
                                    <i class="fas fa-file-alt mr-2"></i>${doc.title}
                                </h4>
                                <div id="doc-${doc.new_id}" class="collapse document-details">
                                    <p><strong>Type:</strong> ${doc.document_type}</p>
                                    ${doc.speakers.length ? `
                                        <p><strong>Speakers:</strong> ${doc.speakers.join(', ')}</p>
                                    ` : ''}
                                    <a href="article.php?id=${doc.new_id}" class="btn btn-sm btn-primary view-details-btn">
                                        <i class="fas fa-eye mr-1"></i>View Details
                                    </a>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
                list.appendChild(dayElement);
            });
        })
        .catch(error => {
            console.error('Error loading Hansard list:', error);
            const list = document.getElementById('hansard-list');
            list.innerHTML = `<p class="error">Error loading Hansard list: ${error.message}</p>`;
        });
}

function loadHansardDetails(newId) {
    fetch(`http://localhost:8080/api/hansard-details.php?id=${encodeURIComponent(newId)}`)
        .then(response => response.json())
        .then(data => {
            const details = document.getElementById('hansard-details');
            
            // Format the content
            const formattedContent = formatHansardContent(data.content);
            
            details.innerHTML = `
                <h2>${data.title}</h2>
                <p><strong><i class="fas fa-calendar-day mr-1"></i>Date:</strong> ${data.date}</p>
                <p><strong><i class="fas fa-file-alt mr-1"></i>Document Type:</strong> ${data.document_type}</p>
                <p><strong><i class="fas fa-globe mr-1"></i>Source:</strong> ${data.source}</p>
                <div class="hansard-content">
                    ${formattedContent}
                </div>
            `;
        })
        .catch(error => {
            console.error('Error loading Hansard details:', error);
            const details = document.getElementById('hansard-details');
            details.innerHTML = `<p class="error">Error loading Hansard details: ${error.message}</p>`;
        });
}

function formatHansardContent(content) {
    // Split the content into paragraphs
    let paragraphs = content.split('\n\n');

    // Process each paragraph
    paragraphs = paragraphs.map(paragraph => {
        // Check if this is a speaker line
        const speakerMatch = paragraph.match(/^([A-Z][A-Z\s.]+):/);
        if (speakerMatch) {
            const speaker = speakerMatch[1];
            const dialogue = paragraph.substring(speakerMatch[0].length).trim();
            return `<p class="speaker-line"><span class="speaker">${speaker}:</span> <span class="dialogue">${dialogue}</span></p>`;
        }
        
        // Check if this is a procedural line (all caps)
        if (paragraph.toUpperCase() === paragraph) {
            return `<p class="procedural">${paragraph}</p>`;
        }
        
        // Regular paragraph
        return `<p class="regular-text">${paragraph}</p>`;
    });

    // Join the paragraphs back together
    return paragraphs.join('');
}