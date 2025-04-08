<script lang="ts">
  import { ArrowRight, Search } from "lucide-svelte";
  import Bookmark from "./Bookmark.svelte";
  import { onMount } from "svelte";
  import { createClient } from "@supabase/supabase-js";

  // Define a type for your bookmark for better safety
  interface BookmarkType {
    id: number;
    url: string;
    created_at: string;
    updated_at: string | null;
    comment: string | null;
    folder: string | null; // Adjust type if 'folder' links to another table
    title: string;
  }

  const supabaseUrl = "https://zglidwrsngurwotngzct.supabase.co";
  const supabaseAnonKey =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpnbGlkd3Jzbmd1cndvdG5nemN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMTAzNTksImV4cCI6MjA1OTY4NjM1OX0.uLVaw_K83mybR3kuhSfJxM4EidTcXgdWYD6UbIoq6H0";

  const supabase = createClient(supabaseUrl, supabaseAnonKey);

  let searchInputElement: HTMLInputElement;
  let searchInputValue: string = $state("");
  // Use the specific type here
  let bookmarks: Array<BookmarkType> = $state([]);
  let editingBookmarks: boolean = $state(false);
  let isLoading: boolean = $state(true); // Optional: for loading state
  let isCreating: boolean = $state(false); // State for creation process
  let fetchError: string | null = $state(null); // Optional: for error state
  let createError: string | null = $state(null); // Optional: for creation error state

  // --- Data Fetching ---
  async function fetchBookmarks() {
    isLoading = true;
    fetchError = null;
    try {
      // Fetch newest first
      let { data, error } = await supabase
        .from("bookmarks")
        .select("*")
        .order("created_at", { ascending: false }); // Order by creation date

      if (error) {
        throw error;
      }
      bookmarks = data ?? [];
      console.log("Bookmarks state updated:", bookmarks);
    } catch (error: any) {
      console.error("Failed to fetch bookmarks:", error);
      fetchError = error.message || "An unknown error occurred.";
      bookmarks = [];
    } finally {
      isLoading = false;
    }
  }

  // --- Data Creation ---
  async function createBookmark(url: string) {
    // Ensure URL has a protocol
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = `https://${url}`;
    }

    isCreating = true;
    createError = null;

    try {
      // Fetch the page title
      let pageTitle = "";
      try {
        // For local testing
        const proxyUrl = `http://localhost:3000/fetch-title?url=${encodeURIComponent(url)}`;
        const response = await fetch(proxyUrl);
        const data = await response.json();
        pageTitle = data.title || "";
      } catch (fetchError) {
        console.warn("Could not fetch page title:", fetchError);
        // Fallback to URL-based title
        pageTitle = url.replace(/^https?:\/\//, "").replace(/^www\./, "");
        if (pageTitle.endsWith("/")) pageTitle = pageTitle.slice(0, -1);
      }

      // Insert the new bookmark with the fetched title
      const { data: newBookmarkData, error } = await supabase
        .from("bookmarks")
        .insert([{ url: url, title: pageTitle || "Untitled" }])
        .select()
        .single();

      if (error) {
        throw error;
      }

      if (newBookmarkData) {
        console.log("New bookmark created:", newBookmarkData);
        // Prepend the new bookmark to the list for immediate UI update
        bookmarks = [newBookmarkData as BookmarkType, ...bookmarks];
        searchInputValue = ""; // Clear input on success
      } else {
        throw new Error("Bookmark created but no data returned."); // Should not happen with .select().single() unless RLS issue
      }
    } catch (error: any) {
      console.error("Failed to create bookmark:", error);
      createError = error.message || "Failed to save bookmark.";
      // Optionally check for specific errors like duplicate URL if you have constraints
      if (
        error.message?.includes(
          "duplicate key value violates unique constraint"
        )
      ) {
        createError = "This URL has already been bookmarked.";
      }
    } finally {
      isCreating = false;
    }
  }

  // --- Data Deletion ---
  async function handleDelete(id: number) {
    console.log("Attempting to delete bookmark with id", id);
    // Optimistic UI update (optional but good UX)
    const originalBookmarks = [...bookmarks];
    bookmarks = bookmarks.filter((b) => b.id !== id);

    try {
      const { error } = await supabase.from("bookmarks").delete().match({ id });

      if (error) {
        throw error; // Throw to be caught below
      }
      console.log("Bookmark deleted successfully", id);
    } catch (error: any) {
      console.error("Delete failed:", error);
      // Revert optimistic update on error
      bookmarks = originalBookmarks;
      // Optionally show an error message to the user
      // createError = `Failed to delete: ${error.message}`; // Reusing createError might be confusing
    }
  }

  // --- Event Handlers ---
  function handleSearchInputKeydown(event: KeyboardEvent) {
    if (event.key === "Enter") {
      event.preventDefault(); // Prevent form submission if it were in a form
      const value = searchInputValue.trim();
      createBookmark(value);
    }
  }

  // --- Lifecycle ---
  onMount(() => {
    searchInputElement.focus();

    document.addEventListener("keydown", (event) => {
      if (event.key === "/") {
        // Avoid focusing if already focused or if inside an input/textarea
        if (
          document.activeElement !== searchInputElement &&
          !["input", "textarea"].includes(
            (event.target as HTMLElement)?.tagName?.toLowerCase()
          )
        ) {
          event.preventDefault();
          searchInputElement.focus();
          searchInputElement.select(); // Select existing text
        }
      }
    });

    fetchBookmarks();
  });
</script>

<main class="p-4 flex flex-col gap-3 font-jetbrains-mono">
  <header class="flex gap-2 items-center font-jetbrains-mono">
    <ArrowRight size="15" /> BOOKMARKS
    <button
      disabled={isCreating}
      onmousedown={() => (editingBookmarks = !editingBookmarks)}
      class="ml-auto border border-gray-200 px-2.5 py-0.5 cursor-pointer hover:bg-gray-100
      disabled:opacity-50 disabled:cursor-not-allowed"
      >{#if editingBookmarks}FINISH{:else}MANAGE{/if}</button
    >
  </header>
  <search
    class="w-full flex items-center gap-3 border-[1.5px] border-gray-300 px-2.5 py-2 pl-3 mb-1 group"
  >
    <Search
      size="15"
      strokeWidth={2.25}
      class="text-gray-400 transition-colors duration-150"
    />
    <input
      type="text"
      class="w-full focus:outline-none font-medium group"
      placeholder="Search or paste URL and press Enter (press '/' to focus)"
      bind:this={searchInputElement}
      bind:value={searchInputValue}
      onkeydown={handleSearchInputKeydown}
      disabled={isCreating}
    />
  </search>
  {#if createError}
    <p class="text-red-500 text-sm mb-2">{createError}</p>
  {/if}

  {#if isLoading}
    <p>Loading bookmarks...</p>
  {:else if fetchError}
    <p class="text-red-600">Error loading bookmarks: {fetchError}</p>
  {:else if bookmarks.length === 0 && !isCreating}
    <p>No bookmarks found. Paste a URL and press Enter to add one.</p>
  {:else}
    {#if isCreating}
      <p>Adding bookmark...</p>
    {/if}
    <div class="flex flex-col gap-1.5">
      {#each bookmarks as bookmark (bookmark.id)}
        <Bookmark
          {bookmark}
          onDelete={handleDelete}
          editing={editingBookmarks}
        />
      {/each}
    </div>
  {/if}
</main>
