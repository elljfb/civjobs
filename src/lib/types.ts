export interface Job {
  id: number;
  title: string;
  department: string;
  salary: string;
  closing_date: string;
  url: string;
  job_locations: { location: string }[];
}
