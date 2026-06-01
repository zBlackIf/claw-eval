export interface ITracking {
  trackingNo: string;
  events: Array<{
    timestamp: string;
    location: string;
    description: string;
  }>;
}
