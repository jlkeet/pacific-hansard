import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SearchResult } from '../models/search-result';

@Component({
  selector: 'app-search-results',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './search-results.html',
  styleUrl: './search-results.scss'
})
export class SearchResultsComponent {
  @Input() results: SearchResult[] = [];
  @Input() loading: boolean = false;
  @Input() query: string = '';

  highlightText(text: string, query: string): string {
    if (!query.trim()) return text;
    
    const queryTerms = query.toLowerCase().split(/\s+/);
    let highlightedText = text;
    
    queryTerms.forEach(term => {
      if (term.length > 2) {
        const regex = new RegExp(`(${term})`, 'gi');
        highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
      }
    });
    
    return highlightedText;
  }

  truncateText(text: string, maxLength: number = 300): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }

  formatDate(dateStr: string): string {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  }

  getConfidenceClass(score: number): string {
    if (score > 0.8) return 'high';
    if (score > 0.5) return 'medium';
    return 'low';
  }

  viewFullDocument(result: SearchResult): void {
    console.log('View full document:', result.doc_id);
    // TODO: Implement full document view modal or route
    alert(`Full document view not yet implemented for document ${result.doc_id}`);
  }
}
