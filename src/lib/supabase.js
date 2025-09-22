import { createClient } from '@supabase/supabase-js';

// Use import.meta.env for Astro environment variables
const supabaseUrl = import.meta.env.SUPABASE_URL;
const supabaseKey = import.meta.env.SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  throw new Error('SUPABASE_URL and SUPABASE_ANON_KEY must be defined in .env file');
}

const supabase = createClient(supabaseUrl, supabaseKey);

export async function getAllJobs() {
  const { data, error } = await supabase
    .from('job_listings')
    .select(`
      id,
      title,
      department,
      salary,
      closing_date,
      url,
      job_locations (
        location
      )
    `);
  if (error) {
    console.error('Supabase getAllJobs error:', error);
    throw error;
  }
  console.log('Raw jobs data:', data);
  return data || [];
}

export async function getUniqueValues(table, column) {
  const { data, error } = await supabase.rpc('get_unique_values', {
    table_name: table,
    column_name: column
  });
  if (error) {
    console.error(`Supabase getUniqueValues error for ${table}.${column}:`, error);
    throw error;
  }
  console.log(`Unique ${column} from ${table}:`, data);
  return data.map(item => item.value);
}

export function getSalaryBucket(salary) {
  if (!salary || salary === 'N/A') return 'Unspecified';
  const match = salary.match(/£([\d,]+)/); // Extract starting salary
  if (!match) return 'Unspecified';
  const startSalary = parseInt(match[1].replace(/,/g, ''), 10);
  if (startSalary < 30000) return 'Under £30,000';
  if (startSalary < 50000) return '£30,000 - £50,000';
  if (startSalary < 70000) return '£50,000 - £70,000';
  return '£70,000+';
}

export async function getUniqueSalaryBuckets() {
  const jobs = await getAllJobs();
  const buckets = new Set(jobs.map(job => getSalaryBucket(job.salary)));
  return Array.from(buckets);
}