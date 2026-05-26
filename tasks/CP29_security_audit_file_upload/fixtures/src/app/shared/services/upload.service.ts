import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class UploadService {
  private apiUrl = '/api/upload';

  constructor(private http: HttpClient) {}

  uploadFile(file: File, endpoint: string): Observable<any> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    // WARNING: No file type validation on client side
    return this.http.post(`${this.apiUrl}/${endpoint}`, formData);
  }

  uploadETLConfig(file: File): Observable<any> {
    return this.uploadFile(file, 'etl-config');
  }

  uploadDatabaseImport(file: File): Observable<any> {
    return this.uploadFile(file, 'import');
  }
}
