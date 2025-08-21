import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { SearchRequest } from './models/search-request';
import { SearchResult } from './models/search-result';

@Injectable({
  providedIn: 'root'
})
export class SearchService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  search(request: SearchRequest): Observable<SearchResult[]> {
    return this.http.post<any>(`${this.apiUrl}/search`, request).pipe(
      map((response: any) => {
        console.log('API Response:', response);
        return response.results || [];
      })
    );
  }

  getStats(): Observable<any> {
    return this.http.get(`${this.apiUrl}/stats`);
  }

  healthCheck(): Observable<any> {
    return this.http.get(`${this.apiUrl}/health`);
  }

  askQuestion(question: string): Observable<any> {
    const request = {
      question: question,
      max_results: 10
    };
    return this.http.post(`${this.apiUrl}/ask`, request);
  }

  getFullDocument(docId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/document/${docId}`);
  }
}
