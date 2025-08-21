import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-filters',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './filters.html',
  styleUrl: './filters.scss'
})
export class FiltersComponent {
  @Input() filters: any = {};
  @Output() filtersChange = new EventEmitter<any>();

  countries = ['Cook Islands', 'Fiji', 'Papua New Guinea'];
  showFilters = false;

  onFilterChange() {
    this.filtersChange.emit({ ...this.filters });
  }

  clearFilters() {
    this.filters = {
      country: '',
      speaker: '',
      chamber: '',
      date_from: '',
      date_to: ''
    };
    this.filtersChange.emit({ ...this.filters });
  }

  toggleFilters() {
    this.showFilters = !this.showFilters;
  }
}
