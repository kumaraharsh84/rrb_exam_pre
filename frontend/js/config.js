const SUPABASE_URL = "https://your-project-id.supabase.co";
const SUPABASE_KEY = "your-anon-key";

function isPlaceholder(value = "") {
  return !value || value.includes("your-project-id") || value.includes("your-anon-key");
}

function isSupabaseConfigured() {
  return !isPlaceholder(SUPABASE_URL) && !isPlaceholder(SUPABASE_KEY);
}

export {
  SUPABASE_URL,
  SUPABASE_KEY,
  isSupabaseConfigured
};
