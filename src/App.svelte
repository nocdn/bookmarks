<script lang="ts">
  import { ArrowRight, PlusCircle, Search, Folder } from "lucide-svelte";
  import Bookmark from "./Bookmark.svelte";
  import { onMount } from "svelte";
  import { createClient } from "@supabase/supabase-js";

  interface BookmarkType {
    id: number;
    url: string;
    created_at: string;
    updated_at: string | null;
    comment: string | null;
    folder_id: number | null;
    title: string;
    faviconColor?: string;
  }

  interface FolderType {
    id: number;
    name: string;
    parent_id: number | null;
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
  let isAddingMultiple = $state(false);
  let folders: Array<FolderType> = $state([]);
  let selectedFolderId: number | null = $state(null);
  let folderOpenStates = $state<Record<number, boolean>>({});
  let dragOverFolderId = $state<number | null | "uncategorized">(null);

  function decodeHtmlEntities(text: string): string {
    if (typeof document !== "undefined") {
      const textarea = document.createElement("textarea");
      textarea.innerHTML = text;
      return textarea.value;
    }
    return text;
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
        faviconRgbCodeString = `rgb(${faviconColor[0]}, ${faviconColor[1]}, ${faviconColor[2]})`;
      } catch (fetchError: any) {
        console.warn("could not fetch or process page title:", fetchError);
        createError = `could not get title: ${fetchError.message}`;
        pageTitle = url.replace(/^https?:\/\//, "").replace(/^www\./, "");
        if (pageTitle.endsWith("/")) pageTitle = pageTitle.slice(0, -1);
        faviconRgbCodeString = "rgb(0, 0, 0)";
      }
      const { data: newBookmarkData, error: insertError } = await supabase
        .from("bookmarks")
        .insert([
          {
            url: url,
            title: pageTitle || "Untitled",
            faviconColor: faviconRgbCodeString,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            folder_id: selectedFolderId,
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
      if (isAddingMultiple) {
        isAddingMultiple = false;
      }
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
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (isAddingMultiple) {
        const values = searchInputValue.split("\n");
        values.forEach((value) => {
          if (value.trim()) {
            createBookmark(value.trim());
          }
        });
      } else {
        const value = searchInputValue.trim();
        if (value) {
          createBookmark(value);
        }
      }
      searchInputValue = "";
    }
  }

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

  let filteredBookmarks = $derived(
    searchInputValue.trim()
      ? bookmarks.filter(
          (b) =>
            fuzzyMatch(b.title || "", searchInputValue) ||
            fuzzyMatch(b.url, searchInputValue)
        )
      : bookmarks
  );

  let groupedBookmarks = $derived({
    uncategorized: filteredBookmarks.filter((b) => !b.folder_id),
    folders: folders
      .map((f) => ({
        folder: f,
        bookmarks: filteredBookmarks.filter((b) => b.folder_id === f.id),
      }))
      .filter(
        (group) => group.bookmarks.length > 0 || searchInputValue.trim() === ""
      ),
  });

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
    fetchFolders();
    return () => {
      document.removeEventListener("keydown", handleGlobalKeydown);
    };
  });

  async function handleEditTitle(id: number, newTitle: string) {
    const originalBookmarks = [...bookmarks];
    bookmarks = bookmarks.map((b) => {
      if (b.id === id) {
        return { ...b, title: newTitle, updated_at: new Date().toISOString() };
      }
      return b;
    });
    try {
      const { error } = await supabase
        .from("bookmarks")
        .update({ title: newTitle, updated_at: new Date().toISOString() })
        .eq("id", id);
      if (error) {
        throw error;
      }
    } catch (error: any) {
      console.error("failed to update bookmark:", error);
      bookmarks = originalBookmarks;
    }
  }

  async function handleEditUrl(id: number, newUrl: string) {
    const originalBookmarks = [...bookmarks];
    bookmarks = bookmarks.map((b) => {
      if (b.id === id) {
        return { ...b, url: newUrl, updated_at: new Date().toISOString() };
      }
      return b;
    });
    try {
      const { error } = await supabase
        .from("bookmarks")
        .update({ url: newUrl, updated_at: new Date().toISOString() })
        .eq("id", id);
      if (error) {
        throw error;
      }
    } catch (error: any) {
      console.error("failed to update bookmark:", error);
      bookmarks = originalBookmarks;
    }
  }

  async function fetchFolders() {
    const { data, error } = await supabase.from("folders").select("*");
    if (error) {
      console.error("failed to fetch folders:", error);
      folders = [];
      return;
    }
    folders = data ?? [];
  }

  async function moveBookmarkToFolder(
    bookmarkId: number,
    targetFolderId: number | null
  ) {
    const bookmarkIndex = bookmarks.findIndex((b) => b.id === bookmarkId);
    if (bookmarkIndex === -1) return;

    const originalFolderId = bookmarks[bookmarkIndex].folder_id;
    if (originalFolderId === targetFolderId) return;

    const originalBookmarks = [...bookmarks];
    bookmarks = bookmarks.map((b) =>
      b.id === bookmarkId
        ? {
            ...b,
            folder_id: targetFolderId,
            updated_at: new Date().toISOString(),
          }
        : b
    );

    try {
      const { error } = await supabase
        .from("bookmarks")
        .update({
          folder_id: targetFolderId,
          updated_at: new Date().toISOString(),
        })
        .eq("id", bookmarkId);

      if (error) {
        throw error;
      }
    } catch (error: any) {
      console.error("failed to move bookmark:", error);
      bookmarks = originalBookmarks;
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "move";
    }
  }

  function handleDrop(event: DragEvent, targetFolderId: number | null) {
    event.preventDefault();
    const bookmarkIdStr = event.dataTransfer?.getData("text/plain");
    dragOverFolderId = null;
    if (!bookmarkIdStr) return;

    const bookmarkId = parseInt(bookmarkIdStr, 10);
    if (!isNaN(bookmarkId)) {
      moveBookmarkToFolder(bookmarkId, targetFolderId);
    }
  }

  function handleFolderDragEnter(folderId: number | null | "uncategorized") {
    dragOverFolderId = folderId;
  }

  function handleFolderDragLeave(event: DragEvent) {
    // Check if the relatedTarget (where the mouse is going) is still within the drop zone
    // If it is, we don't want to clear the highlight yet.
    const currentTarget = event.currentTarget as HTMLElement;
    const relatedTarget = event.relatedTarget as HTMLElement;
    if (
      !currentTarget ||
      !relatedTarget ||
      !currentTarget.contains(relatedTarget)
    ) {
      dragOverFolderId = null;
    }
  }

  $effect(() => {
    if (bookmarks.length === 0) {
      editingBookmarks = false;
    }
  });
</script>

<main class="p-6 flex flex-col gap-3 font-jetbrains-mono min-h-screen">
  <header class="flex gap-2 items-center font-jetbrains-mono flex-shrink-0">
    <ArrowRight size="15" /> BOOKMARKS
    <button
      disabled={isCreating}
      onmousedown={() => (isAddingMultiple = !isAddingMultiple)}
      class="ml-auto border border-gray-200 px-2.5 py-0.5 cursor-pointer hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      IMPORT
    </button>
    <button
      disabled={isCreating || isLoading || bookmarks.length === 0}
      onmousedown={() => (editingBookmarks = !editingBookmarks)}
      class="border border-gray-200 px-2.5 py-0.5 cursor-pointer hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {#if editingBookmarks}
        FINISH
      {:else}
        MANAGE
      {/if}
    </button>
  </header>
  <search
    class="w-full flex items-center gap-3 border-[1.5px] border-gray-300 px-2.5 py-2 pl-3 mb-1 group flex-shrink-0"
  >
    {#if isAddingMultiple}
      <PlusCircle
        size="15"
        strokeWidth={2.25}
        class="text-gray-400 transition-colors duration-150 group-focus-within:text-blue-600 mb-auto mt-[5px]"
      />
    {:else}
      <Search
        size="15"
        strokeWidth={2.25}
        class="text-gray-400 transition-colors duration-150 group-focus-within:text-blue-600"
      />
    {/if}
    {#if isAddingMultiple}
      <textarea
        class="w-full focus:outline-none font-medium group min-h-24"
        placeholder="Paste URLs, one per line and press Enter (press '/' to focus)"
        bind:this={searchInputElement}
        bind:value={searchInputValue}
        onkeydown={handleSearchInputKeydown}
        disabled={isCreating}
      ></textarea>
    {:else}
      <input
        type="text"
        class="w-full focus:outline-none font-medium group"
        placeholder="Search or paste URL and press Enter (press '/' to focus)"
        bind:this={searchInputElement}
        bind:value={searchInputValue}
        onkeydown={handleSearchInputKeydown}
        disabled={isCreating}
      />
    {/if}
    <select
      bind:value={selectedFolderId}
      class="ml-2 flex-shrink-0 p-1 border border-gray-300 rounded"
    >
      <option value={null}>Uncategorized</option>
      {#each folders as folder}
        <option value={folder.id}>{folder.name}</option>
      {/each}
    </select>
  </search>
  {#if createError}
    <p class="text-red-500 text-sm mb-2 flex-shrink-0">{createError}</p>
  {/if}
  {#if isLoading}
    <p class="flex-shrink-0">Loading bookmarks...</p>
  {:else if fetchError}
    <p class="text-red-600 flex-shrink-0">
      Error loading bookmarks: {fetchError}
    </p>
  {:else if bookmarks.length === 0 && !isCreating}
    <p class="text-gray-400 font-[450] flex-shrink-0">
      No bookmarks found. Paste a URL and press Enter to add one.
    </p>
  {:else}
    {#if isCreating && !createError}
      <p class="flex-shrink-0">Adding bookmark...</p>
    {/if}
    <div class="flex flex-col gap-5 flex-grow">
      {#each groupedBookmarks.folders as group (group.folder.id)}
        {@const isOpen = folderOpenStates[group.folder.id] ?? true}
        {@const isDragOverTarget = dragOverFolderId === group.folder.id}
        <div
          ondragover={handleDragOver}
          ondrop={(e) => handleDrop(e, group.folder.id)}
          ondragenter={() => handleFolderDragEnter(group.folder.id)}
          ondragleave={handleFolderDragLeave}
          role="button"
          tabindex="0"
          class:bg-blue-50={isDragOverTarget}
          class="p-2 rounded-md transition-colors duration-150 flex-shrink-0"
        >
          <h3 class="flex items-center gap-2 font-geist font-medium mb-1">
            <button
              onclick={() => (folderOpenStates[group.folder.id] = !isOpen)}
              class="flex items-center gap-2 cursor-pointer hover:text-blue-600"
            >
              <Folder size="15" />
              {group.folder.name}
            </button>
          </h3>
          {#if isOpen}
            <div
              class="flex flex-col gap-1 border-l-2 border-gray-200 ml-[6.75px] pl-3.5 mt-2"
            >
              {#if group.bookmarks.length > 0}
                {#each group.bookmarks as bookmark (bookmark.id)}
                  <Bookmark
                    {bookmark}
                    onDelete={handleDelete}
                    editing={editingBookmarks}
                    onEditTitle={handleEditTitle}
                    onEditUrl={handleEditUrl}
                  />
                {/each}
              {:else if !isDragOverTarget}
                <p class="text-xs text-gray-400 italic pl-1">Empty folder</p>
              {/if}
            </div>
          {/if}
        </div>
      {/each}

      <div
        ondragover={handleDragOver}
        ondrop={(e) => handleDrop(e, null)}
        ondragenter={() => handleFolderDragEnter("uncategorized")}
        ondragleave={handleFolderDragLeave}
        role="button"
        tabindex="0"
        class:bg-blue-50={dragOverFolderId === "uncategorized"}
        class="flex flex-col gap-1 mt-2 p-2 rounded-md transition-colors duration-150 min-h-40 flex-grow"
      >
        {#if groupedBookmarks.uncategorized.length > 0}
          <h3
            class="font-geist font-medium text-gray-500 mb-1 ml-1 flex-shrink-0"
          >
            Uncategorized
          </h3>
          {#each groupedBookmarks.uncategorized as bookmark (bookmark.id)}
            <Bookmark
              {bookmark}
              onDelete={handleDelete}
              editing={editingBookmarks}
              onEditTitle={handleEditTitle}
              onEditUrl={handleEditUrl}
            />
          {/each}
        {/if}
        {#if groupedBookmarks.uncategorized.length === 0 && dragOverFolderId !== "uncategorized"}
          <div
            class="flex-grow flex items-center justify-center text-gray-400 italic"
          >
            Drag items here to uncategorize
          </div>
        {/if}
      </div>
    </div>
  {/if}
</main>
