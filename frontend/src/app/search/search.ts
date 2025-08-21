import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SearchService } from '../search';
import { SearchRequest } from '../models/search-request';
import { SearchResult } from '../models/search-result';
import { SearchResultsComponent } from '../search-results/search-results';
import { FiltersComponent } from '../filters/filters';

@Component({
  selector: 'app-search',
  standalone: true,
  imports: [CommonModule, FormsModule, SearchResultsComponent, FiltersComponent],
  templateUrl: './search.html',
  styleUrl: './search.scss'
})
export class SearchComponent implements OnInit {
  query = '';
  results: SearchResult[] = [];
  loading = false;
  stats: any = null;
  
  filters = {
    country: '',
    speaker: '',
    chamber: '',
    date_from: '',
    date_to: ''
  };

  constructor(private searchService: SearchService) {}

  ngOnInit() {
    this.loadStats();
  }

  onSearch() {
    if (!this.query.trim()) return;

    console.log('Starting search for:', this.query);
    this.loading = true;
    
    const request: SearchRequest = {
      query: this.query,
      top_k: 10,
      filters: this.filters
    };

    console.log('Search request:', request);

    this.searchService.search(request).subscribe({
      next: (results) => {
        console.log('Search results received:', results);
        this.results = results;
        this.loading = false;
      },
      error: (error) => {
        console.error('Search error:', error);
        this.loading = false;
      }
    });
  }

  onFiltersChange(newFilters: any) {
    this.filters = { ...newFilters };
    if (this.query.trim()) {
      this.onSearch();
    }
  }

  loadStats() {
    this.searchService.getStats().subscribe({
      next: (stats) => {
        this.stats = stats;
      },
      error: (error) => {
        console.error('Stats error:', error);
      }
    });
  }
}
