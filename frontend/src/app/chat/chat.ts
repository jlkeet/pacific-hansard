import { Component, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { SearchService } from '../search';
import { ChatMessage } from '../models/chat-message';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrl: './chat.scss'
})
export class ChatComponent {
  messages: ChatMessage[] = [];
  currentQuestion = '';
  isLoading = false;
  selectedSource: any = null;
  showSourceModal = false;

  constructor(private searchService: SearchService, private sanitizer: DomSanitizer) {
    // Add welcome message
    this.messages.push({
      id: '1',
      content: 'Hello! I\'m your Pacific Hansard AI assistant powered by DeepSeek R1 8B. Ask me anything about parliamentary proceedings from Cook Islands, Fiji, and Papua New Guinea!',
      timestamp: new Date(),
      isUser: false
    });
  }

  sendMessage() {
    if (!this.currentQuestion.trim() || this.isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: this.currentQuestion,
      timestamp: new Date(),
      isUser: true
    };

    this.messages.push(userMessage);

    // Add loading message
    const loadingMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      content: 'Thinking...',
      timestamp: new Date(),
      isUser: false,
      isLoading: true
    };

    this.messages.push(loadingMessage);
    this.isLoading = true;

    const question = this.currentQuestion;
    this.currentQuestion = '';

    // Call DeepSeek API
    this.searchService.askQuestion(question).subscribe({
      next: (response) => {
        // Remove loading message
        this.messages = this.messages.filter(m => !m.isLoading);

        // Add AI response
        const aiMessage: ChatMessage = {
          id: Date.now().toString(),
          content: response.answer,
          timestamp: new Date(),
          isUser: false,
          sources: response.sources || []
        };

        this.messages.push(aiMessage);
        this.isLoading = false;
      },
      error: (error) => {
        // Remove loading message
        this.messages = this.messages.filter(m => !m.isLoading);

        // Add error message
        const errorMessage: ChatMessage = {
          id: Date.now().toString(),
          content: 'Sorry, I encountered an error processing your question. Please try again.',
          timestamp: new Date(),
          isUser: false
        };

        this.messages.push(errorMessage);
        this.isLoading = false;
        console.error('Chat error:', error);
      }
    });
  }

  onKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  setQuestion(question: string) {
    this.currentQuestion = question;
  }

  trackMessage(index: number, message: ChatMessage): string {
    return message.id;
  }

  formatMessage(content: string, sources?: any[]): SafeHtml {
    if (!content) return this.sanitizer.bypassSecurityTrustHtml('');
    
    console.log('📝 Formatting message with', sources?.length || 0, 'sources');
    
    // Split content into paragraphs and format
    let formatted = content
      // Convert double newlines to paragraph breaks
      .replace(/\n\n+/g, '</p><p>')
      // Convert single newlines to line breaks within paragraphs  
      .replace(/\n/g, '<br>')
      // Make citations clickable - create clickable superscript elements
      // Handle both [#0] and [0] formats
      .replace(/\[#?(\d+)\]/g, (match, index) => {
        console.log('🔗 Creating clickable citation:', match, 'with index:', index);
        return `<sup class="citation clickable" data-source-index="${index}" title="Click to view source">[${index}]</sup>`;
      })
      // Wrap in paragraph tags if not already wrapped
      .replace(/^(?!<p>)/, '<p>')
      .replace(/(?<!<\/p>)$/, '</p>');
    
    // Clean up empty paragraphs
    formatted = formatted.replace(/<p><\/p>/g, '');
    
    // Use bypassSecurityTrustHtml to preserve our custom data attributes
    return this.sanitizer.bypassSecurityTrustHtml(formatted);
  }

  onCitationClick(event: Event, message: ChatMessage): void {
    console.log('🖱️ CLICK EVENT FIRED:', event);
    console.log('🖱️ Event target:', event.target);
    console.log('🖱️ Message sources available:', message.sources?.length);
    
    // Look for citation elements in the event path
    let target = event.target as HTMLElement;
    
    // Check if we clicked on a citation or if citation is in the path
    while (target && target !== event.currentTarget) {
      console.log('🔍 Checking element:', {
        tagName: target.tagName,
        className: target.className,
        classList: Array.from(target.classList),
        innerHTML: target.innerHTML,
        textContent: target.textContent
      });
      
      if (target.classList.contains('citation') && target.classList.contains('clickable')) {
        event.preventDefault();
        event.stopPropagation();
        
        // Extract citation number from text content like "[0]", "[1]", etc.
        const citationText = target.textContent || '';
        const match = citationText.match(/\[(\d+)\]/);
        
        if (match) {
          const sourceIndex = parseInt(match[1]);
          console.log('✅ CITATION FOUND! Source index:', sourceIndex, 'Available sources:', message.sources?.length);
          console.log('📋 All sources:', message.sources);
          console.log('🎯 Looking for source at index:', sourceIndex);
          
          if (message.sources && message.sources[sourceIndex]) {
            this.selectedSource = message.sources[sourceIndex];
            this.showSourceModal = true;
            console.log('🎯 MODAL OPENED with source:', this.selectedSource);
            return;
          } else {
            console.log('❌ No source found at index:', sourceIndex);
            console.log('Available indices:', message.sources?.map((_, i) => i));
          }
        } else {
          console.log('❌ Could not parse citation number from:', citationText);
        }
      }
      target = target.parentElement as HTMLElement;
    }
    
    console.log('❌ No citation found in click path');
  }

  closeSourceModal(): void {
    this.showSourceModal = false;
    this.selectedSource = null;
  }

  formatSourceDate(dateString: string): string {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  }

  @HostListener('document:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent): void {
    if (event.key === 'Escape' && this.showSourceModal) {
      this.closeSourceModal();
    }
  }

  openSourceModal(source: any): void {
    console.log('📖 Opening source modal for:', source);
    this.selectedSource = source;
    this.showSourceModal = true;
  }

  viewFullDocument(source: any): void {
    console.log('🔗 viewFullDocument called with:', source);
    
    if (source.url && source.url.trim()) {
      console.log('🌐 Opening source URL:', source.url);
      // If source has a URL, open it in a new tab
      window.open(source.url, '_blank');
    } else {
      console.log('📄 No URL available, requesting full document from API');
      
      // Request the full document from the backend API
      if (source.doc_id) {
        this.searchService.getFullDocument(source.doc_id).subscribe({
          next: (fullDoc: any) => {
            console.log('📄 Received full document:', fullDoc);
            this.openFullDocumentWindow(source, fullDoc.content || fullDoc.text || 'No content available');
          },
          error: (error: any) => {
            console.error('❌ Error fetching full document:', error);
            // Fallback to the chunk content we have
            this.openFullDocumentWindow(source, source.full_text || source.text || 'No content available');
          }
        });
      } else {
        console.log('📄 No doc_id available, using chunk content');
        // Fallback to the chunk content we have
        this.openFullDocumentWindow(source, source.full_text || source.text || 'No content available');
      }
    }
  }

  private openFullDocumentWindow(source: any, content: string): void {
    const newWindow = window.open('', '_blank');
    if (newWindow) {
      const isChunkContent = content === (source.full_text || source.text);
      
      newWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>Parliamentary Document - ${source.country} - ${this.formatSourceDate(source.date)}</title>
          <style>
            body { 
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
              line-height: 1.6; 
              max-width: 900px; 
              margin: 0 auto; 
              padding: 2rem;
              color: #333;
              background: #f8f9fa;
            }
            .container {
              background: white;
              padding: 2rem;
              border-radius: 12px;
              box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .header {
              border-bottom: 2px solid #e9ecef;
              padding-bottom: 1rem;
              margin-bottom: 2rem;
            }
            .metadata {
              background: #f8f9fa;
              padding: 1.5rem;
              border-radius: 8px;
              margin-bottom: 2rem;
              border-left: 4px solid #007bff;
            }
            .content {
              white-space: pre-wrap;
              font-size: 1rem;
              line-height: 1.8;
              background: #fafbfc;
              padding: 1.5rem;
              border-radius: 8px;
              border: 1px solid #e1e4e8;
            }
            .content-type {
              background: ${isChunkContent ? '#fff3cd' : '#d4edda'};
              color: ${isChunkContent ? '#856404' : '#155724'};
              padding: 0.5rem 1rem;
              border-radius: 4px;
              margin-bottom: 1rem;
              font-size: 0.9rem;
              font-weight: 500;
            }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>📄 Parliamentary Document</h1>
            </div>
            <div class="metadata">
              <p><strong>Country:</strong> ${source.country}</p>
              <p><strong>Date:</strong> ${this.formatSourceDate(source.date)}</p>
              <p><strong>Speaker:</strong> ${source.speaker}</p>
              ${source.doc_id ? `<p><strong>Document ID:</strong> ${source.doc_id}</p>` : ''}
              ${source.chunk_index !== undefined ? `<p><strong>Chunk:</strong> ${source.chunk_index}</p>` : ''}
            </div>
            <div class="content-type">
              ${isChunkContent ? '⚠️ Showing Document Excerpt (full document not available)' : '✅ Complete Document'}
            </div>
            <div class="content">
              ${content.replace(/\n/g, '<br>')}
            </div>
          </div>
        </body>
        </html>
      `);
      newWindow.document.close();
    }
  }
}
