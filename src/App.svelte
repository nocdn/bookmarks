<script lang="ts">
  import { ArrowRight, Search } from "lucide-svelte";
  import Bookmark from "./Bookmark.svelte";
  import { onMount } from "svelte";
  import { createClient } from "@supabase/supabase-js";

  interface BookmarkType {
    id: number;
    url: string;
    created_at: string;
    updated_at: string | null;
    comment: string | null;
    folder: string | null;
    title: string;
  }

  const supabaseUrl = "https://zglidwrsngurwotngzct.supabase.co";
  const supabaseAnonKey =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpnbGlkd3Jzbmd1cndvdG5nemN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMTAzNTksImV4cCI6MjA1OTY4NjM1OX0.uLVaw_K83mybR3kuhSfJxM4EidTcXgdWYD6UbIoq6H0";

  const supabase = createClient(supabaseUrl, supabaseAnonKey);

  let searchInputElement: HTMLInputElement;
  let searchInputValue: string = $state("");
  let bookmarks: Array<BookmarkType> = $state([]);
  let editingBookmarks: boolean = $state(false);
  let isLoading: boolean = $state(true);
  let isCreating: boolean = $state(false);
  let fetchError: string | null = $state(null);
  let createError: string | null = $state(null);

  // helper to decode html entities
  function decodeHtmlEntities(text: string): string {
    if (typeof document !== "undefined") {
      const textarea = document.createElement("textarea");
      textarea.innerHTML = text;
      return textarea.value;
    }
    return text; // return original text if document not available (SSR)
  }

  async function fetchBookmarks() {
    isLoading = true;
    fetchError = null;
    try {
      let { data, error } = await supabase
        .from("bookmarks")
        .select("*")
        .order("created_at", { ascending: false });

      if (error) {
        throw error;
      }
      bookmarks = data ?? [];
    } catch (error: any) {
      console.error("failed to fetch bookmarks:", error);
      fetchError = error.message || "an unknown error occurred";
      bookmarks = [];
    } finally {
      isLoading = false;
    }
  }

  async function createBookmark(url: string) {
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = `https://${url}`;
    }

    isCreating = true;
    createError = null;

    try {
      let pageTitle = "";
      let faviconColor = "";
      let faviconRgbCodeString = "";
      try {
        const proxyUrl = `http://84.8.144.162:8030/api/fetch-title?url=${encodeURIComponent(url)}`;
        const response = await fetch(proxyUrl);

        if (!response.ok) {
          const errorData = await response
            .json()
            .catch(() => ({ detail: "failed to parse error response" }));
          throw new Error(
            errorData.detail ||
              `proxy request failed with status: ${response.status}`
          );
        }

        const data = await response.json();
        pageTitle = data.title ? decodeHtmlEntities(data.title) : "";
        faviconColor = data.faviconColor || "black";
        console.log("favicon color from db:", faviconColor);
        faviconRgbCodeString = `rgb(${faviconColor[0]}, ${
          faviconColor[1]
        }, ${faviconColor[2]})`;
        console.log("favicon rgb code:", faviconRgbCodeString);
      } catch (fetchError: any) {
        console.warn("could not fetch or process page title:", fetchError);
        createError = `could not get title: ${fetchError.message}`;
        pageTitle = url.replace(/^https?:\/\//, "").replace(/^www\./, "");
        if (pageTitle.endsWith("/")) pageTitle = pageTitle.slice(0, -1);
      }

      const { data: newBookmarkData, error: insertError } = await supabase
        .from("bookmarks")
        .insert([
          {
            url: url,
            title: pageTitle || "Untitled",
            faviconColor: faviconRgbCodeString,
          },
        ])
        .select()
        .single();

      if (insertError) {
        throw insertError;
      }

      if (newBookmarkData) {
        bookmarks = [newBookmarkData as BookmarkType, ...bookmarks];
        searchInputValue = "";
      } else {
        throw new Error("bookmark created but no data returned");
      }
    } catch (error: any) {
      console.error("failed to create bookmark:", error);
      createError = createError || error.message || "failed to save bookmark";
      if (
        error.message?.includes(
          "duplicate key value violates unique constraint"
        )
      ) {
        createError = "this url has already been bookmarked";
      }
    } finally {
      isCreating = false;
    }
  }

  async function handleDelete(id: number) {
    const originalBookmarks = [...bookmarks];
    bookmarks = bookmarks.filter((b) => b.id !== id);

    try {
      const { error } = await supabase.from("bookmarks").delete().match({ id });
      if (error) {
        throw error;
      }
    } catch (error: any) {
      console.error("delete failed:", error);
      bookmarks = originalBookmarks;
    }
  }

  function handleSearchInputKeydown(event: KeyboardEvent) {
    if (event.key === "Enter") {
      event.preventDefault();
      const value = searchInputValue.trim();
      if (value) {
        createBookmark(value);
      }
    }
  }

  // fuzzy match function to check if all characters in the pattern exist
  // in the text (in order)
  function fuzzyMatch(text: string, pattern: string): boolean {
    if (!pattern) return true;
    text = text.toLowerCase();
    pattern = pattern.toLowerCase();
    let j = 0;
    for (let i = 0; i < text.length && j < pattern.length; i++) {
      if (text[i] === pattern[j]) {
        j++;
      }
    }
    return j === pattern.length;
  }

  // reactively filter bookmarks based on search input
  // by checking title and url fields
  let filteredBookmarks = $derived(
    searchInputValue.trim()
      ? bookmarks.filter(
          (b) =>
            fuzzyMatch(b.title, searchInputValue) ||
            fuzzyMatch(b.url, searchInputValue)
        )
      : bookmarks
  );

  onMount(() => {
    searchInputElement?.focus();

    const handleGlobalKeydown = (event: KeyboardEvent) => {
      if (event.key === "/") {
        if (
          document.activeElement !== searchInputElement &&
          !["input", "textarea"].includes(
            (event.target as HTMLElement)?.tagName?.toLowerCase()
          )
        ) {
          event.preventDefault();
          searchInputElement?.focus();
          searchInputElement?.select();
        }
      }
    };

    document.addEventListener("keydown", handleGlobalKeydown);
    fetchBookmarks();

    return () => {
      document.removeEventListener("keydown", handleGlobalKeydown);
    };
  });

  async function handleEdit(id: number, newTitle: string) {
    // eagerly update the bookmarks array to show new title immediately
    const originalBookmarks = [...bookmarks];
    bookmarks = bookmarks.map((b) => {
      if (b.id === id) {
        return {
          ...b,
          title: newTitle,
        };
      }
      return b;
    });

    try {
      const { error } = await supabase
        .from("bookmarks")
        .update({ title: newTitle })
        .eq("id", id);
      if (error) {
        throw error;
      }
    } catch (error: any) {
      console.error("failed to update bookmark:", error);
      bookmarks = originalBookmarks;
    }
  }
</script>

<main class="p-4 flex flex-col gap-3 font-jetbrains-mono">
  <header class="flex gap-2 items-center font-jetbrains-mono">
    <ArrowRight size="15" /> BOOKMARKS
    <button
      disabled={isCreating}
      onmousedown={() => (editingBookmarks = !editingBookmarks)}
      class="ml-auto border border-gray-200 px-2.5 py-0.5 cursor-pointer hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {#if editingBookmarks}
        FINISH
      {:else}
        MANAGE
      {/if}
    </button>
  </header>
  <search
    class="w-full flex items-center gap-3 border-[1.5px] border-gray-300 px-2.5 py-2 pl-3 mb-1 group"
  >
    <Search
      size="15"
      strokeWidth={2.25}
      class="text-gray-400 transition-colors duration-150 group-focus-within:text-blue-600"
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
    <p class="text-gray-600 font-[450]">
      No bookmarks found. Paste a URL and press Enter to add one.
    </p>
  {:else}
    {#if isCreating && !createError}
      <p>Adding bookmark...</p>
    {/if}
    <div class="flex flex-col gap-1.5">
      {#each filteredBookmarks as bookmark (bookmark.id)}
        <Bookmark
          {bookmark}
          onDelete={handleDelete}
          editing={editingBookmarks}
          onEdit={handleEdit}
        />
      {/each}
    </div>
  {/if}
</main>
