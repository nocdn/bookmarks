<script lang="ts">
  import {
    ArrowRight,
    PlusCircle,
    Search,
    Folder,
    Inbox,
    HeartCrack,
    Sparkles,
  } from "lucide-svelte";
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
    color: string;
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
  let currentSelectedFolderId = $state<number | null>(null);
  let dragOverFolderId = $state<number | null | "uncategorized">(null);
  let isCreatingFolder = $state(false);
  let newFolderName = $state("");
  let newFolderColor = $state("rgb(0, 0, 0)");
  let showingLLMicon = $state(false);

  const geminiApiKey = import.meta.env.VITE_GEMINI_API_KEY;

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
        // ensure faviconcolor is an array before accessing elements
        if (Array.isArray(faviconColor) && faviconColor.length >= 3) {
          faviconRgbCodeString = `rgb(${faviconColor[0]}, ${faviconColor[1]}, ${faviconColor[2]})`;
        } else {
          faviconRgbCodeString = "rgb(0, 0, 0)"; // default black
        }
      } catch (fetchError: any) {
        console.warn("could not fetch or process page title:", fetchError);
        createError = `could not get title: ${fetchError.message}`;
        pageTitle = url.replace(/^https?:\/\//, "").replace(/^www\./, "");
        if (pageTitle.endsWith("/")) pageTitle = pageTitle.slice(0, -1);
        faviconRgbCodeString = "rgb(0, 0, 0)";
      }
      getLLMfolder(url);
      const { data: newBookmarkData, error: insertError } = await supabase
        .from("bookmarks")
        .insert([
          {
            url: url,
            title: pageTitle || "Untitled",
            faviconColor: faviconRgbCodeString,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            // use the currently selected folder when creating
            folder_id: currentSelectedFolderId,
          },
        ])
        .select()
        .single();
      if (insertError) {
        throw insertError;
      }
      if (newBookmarkData) {
        // add to the beginning of the list
        bookmarks = [newBookmarkData as BookmarkType, ...bookmarks];
        searchInputValue = ""; // clear search on successful add
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
        isAddingMultiple = false; // turn off multi-add mode after submission
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
      bookmarks = originalBookmarks; // revert on error
    }
  }

  async function handleSearchInputKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (isAddingMultiple) {
        const values = searchInputValue.split("\n");
        values.forEach((value) => {
          if (value.trim()) {
            createBookmark(value.trim());
          }
        });
        // searchInputValue = ""; // cleared inside createBookmark if successful
      } else {
        const value = searchInputValue.trim();
        if (value) {
          createBookmark(value);
        }
      }
    }
    if (event.key === "Enter" && event.altKey) {
      event.preventDefault();
      console.log("using LLM to get folder id");
      const value = searchInputValue.trim();
      if (value) {
        currentSelectedFolderId = await getLLMfolder(value);
      }
    }
  }

  document.addEventListener("keydown", (event) => {
    if (
      event.key === "Alt" &&
      searchInputElement?.contains(document.activeElement)
    ) {
      showingLLMicon = true;
    }
  });
  document.addEventListener("keyup", (event) => {
    if (event.key === "Alt") {
      showingLLMicon = false;
    }
  });

  function fuzzyMatch(text: string, pattern: string): boolean {
    if (!pattern) return true; // match if pattern is empty
    text = text.toLowerCase();
    pattern = pattern.toLowerCase();
    let j = 0; // pointer for pattern
    for (let i = 0; i < text.length && j < pattern.length; i++) {
      if (text[i] === pattern[j]) {
        j++;
      }
    }
    return j === pattern.length; // true if entire pattern was matched
  }

  // filter bookmarks based on search first
  let searchedBookmarks = $derived(
    bookmarks.filter(
      (b) =>
        fuzzyMatch(b.title || "", searchInputValue) ||
        fuzzyMatch(b.url, searchInputValue)
    )
  );

  // then filter based on the selected folder
  let displayedBookmarks = $derived(
    searchedBookmarks.filter((b) => b.folder_id === currentSelectedFolderId)
  );

  // remove old groupedBookmarks logic
  /*
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
  */

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
    // update the state immediately for responsiveness
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
      bookmarks = originalBookmarks; // revert on error
    }
  }

  async function handleEditUrl(id: number, newUrl: string) {
    const originalBookmarks = [...bookmarks];
    // update the state immediately
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
      bookmarks = originalBookmarks; // revert on error
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
    console.log("fetched folders:", folders);
  }

  async function moveBookmarkToFolder(
    bookmarkId: number,
    targetFolderId: number | null
  ) {
    const bookmarkIndex = bookmarks.findIndex((b) => b.id === bookmarkId);
    if (bookmarkIndex === -1) return;

    const originalFolderId = bookmarks[bookmarkIndex].folder_id;
    // prevent unnecessary updates if dropped onto the same folder
    if (originalFolderId === targetFolderId) return;

    const originalBookmarks = [...bookmarks];
    // update state immediately
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
      bookmarks = originalBookmarks; // revert on error
    }
  }

  // --- drag and drop handlers ---
  function handleDragOver(event: DragEvent) {
    event.preventDefault(); // necessary to allow drop
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "move";
    }
  }

  function handleDrop(event: DragEvent, targetFolderId: number | null) {
    event.preventDefault();
    const bookmarkIdStr = event.dataTransfer?.getData("text/plain");
    dragOverFolderId = null; // clear visual feedback
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
    // check if the mouse is leaving the drop zone element entirely
    const currentTarget = event.currentTarget as HTMLElement;
    const relatedTarget = event.relatedTarget as Node;
    // if relatedTarget is null or not contained within currentTarget, clear the highlight
    if (!relatedTarget || !currentTarget.contains(relatedTarget)) {
      dragOverFolderId = null;
    }
  }
  // --- end drag and drop handlers ---

  $effect(() => {
    // automatically turn off editing mode if bookmarks list becomes empty
    if (bookmarks.length === 0) {
      editingBookmarks = false;
    }
  });

  async function handleCreateFolder() {
    isCreatingFolder = false;
    // create folder in the database
    const { data: newFolderData, error: insertError } = await supabase
      .from("folders")
      .insert([
        {
          name: newFolderName,
          color: newFolderColor,
          parent_id: null,
        },
      ]);
    if (insertError) {
      console.error("failed to create folder:", insertError);
      return;
    }
    console.log("created folder:", newFolderData);
    fetchFolders();
  }

  async function getLLMfolder(link: string) {
    const foldersString = JSON.stringify(
      folders.map((f) => ({ id: f.id, name: f.name })),
      null,
      2
    );
    const systemPrompt = `The user will provide a url, then you will respond with JUST the id of the folder you think it should go into. Respond with no formatting, no markdown, no quotes, just the folder ID as the text. The available folders and folder ID's:\n${foldersString}`;

    const response = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${geminiApiKey}`,
        },
        body: JSON.stringify({
          model: "gemini-2.0-flash",
          messages: [
            {
              role: "system",
              content: systemPrompt,
            },
            { role: "user", content: link },
          ],
        }),
      }
    );

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
    console.log("gemini response:", data.choices[0].message.content);
    return parseInt(data.choices[0].message.content);
  }
</script>

<main class="p-6 flex flex-col gap-3 font-jetbrains-mono min-h-screen">
  <!-- header remains the same -->
  <header class="flex gap-2 items-center font-jetbrains-mono flex-shrink-0">
    <ArrowRight size="15" /> BOOKMARKS
    <button
      disabled={isCreating}
      onmousedown={() => (isAddingMultiple = !isAddingMultiple)}
      class="ml-auto border border-gray-200 px-2.5 py-0.5 cursor-pointer hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {#if isAddingMultiple}
        ADDING MULTIPLE
      {:else}
        IMPORT
      {/if}
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

  <!-- search bar remains the same -->
  <search
    class="w-full flex items-center gap-3 border border-gray-300 px-2.5 py-2 pl-3 mb-1 group flex-shrink-0"
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
        class="w-full focus:outline-none font-medium group min-h-24 resize-y"
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
      {#if showingLLMicon}
        <Sparkles size={18} color="blue" class="opacity-60" />
      {/if}
    {/if}
    <!-- folder select dropdown is less useful now, hide or remove? let's hide it for now -->
    <!--
    <select
      bind:value={currentSelectedFolderId}
      class="ml-2 flex-shrink-0 p-1 border border-gray-300 rounded hidden sm:block"
    >
      <option value={null}>Uncategorized</option>
      {#each folders as folder}
        <option value={folder.id}>{folder.name}</option>
      {/each}
    </select>
     -->
  </search>

  <!-- errors and loading indicators -->
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

    <!-- main content area: sidebar + bookmarks list -->
    <div
      id="separated"
      class="grid grid-cols-[auto_1fr] gap-6 flex-grow min-h-0"
    >
      <!-- sidebar -->
      <folders class="flex flex-col gap-1 font-medium w-62 flex-shrink-0 pr-4">
        <!-- uncategorized button -->
        <button
          id="folder-uncategorized"
          class="{currentSelectedFolderId === null
            ? 'font-semibold bg-gray-100'
            : ''} flex items-center gap-2 p-1.5 px-2.5 hover:bg-gray-100 w-full text-left"
          ondragover={handleDragOver}
          ondrop={(e) => handleDrop(e, null)}
          ondragenter={() => handleFolderDragEnter("uncategorized")}
          ondragleave={handleFolderDragLeave}
          class:bg-blue-50={dragOverFolderId === "uncategorized"}
          onmousedown={() => {
            currentSelectedFolderId = null;
          }}
          ><Inbox
            size={16}
            strokeWidth={currentSelectedFolderId === null ? 3 : 2.5}
            class="text-gray-600"
          />
          Uncategorized
        </button>

        <!-- fetched folders -->
        {#each folders as folder (folder.id)}
          <button
            id="folder-{folder.id}"
            class="{currentSelectedFolderId === folder.id
              ? 'font-semibold bg-gray-100'
              : ''} flex items-center gap-2 p-1.5 px-2.5 hover:bg-gray-100 w-full text-left"
            ondragover={handleDragOver}
            ondrop={(e) => handleDrop(e, folder.id)}
            ondragenter={() => handleFolderDragEnter(folder.id)}
            ondragleave={handleFolderDragLeave}
            class:bg-blue-50={dragOverFolderId === folder.id}
            style="color: {folder.color || 'inherit'};"
            onmousedown={() => {
              currentSelectedFolderId = folder.id;
            }}
            ><Folder size={16} strokeWidth={2.75} />
            {folder.name}</button
          >
        {/each}
        <button
          id="new-folder"
          class="mr-auto p-1.5 px-2.5 pl-[12.5px] text-gray-500 hover:bg-gray-100 rounded-md flex items-center gap-2"
          onmousedown={() => {
            if (!isCreatingFolder) {
              isCreatingFolder = !isCreatingFolder;
            }
          }}
        >
          {#if isCreatingFolder}
            <input
              type="text"
              class="w-full focus:outline-none font-medium"
              placeholder="New folder name"
              bind:value={newFolderName}
              onkeydown={(e) => {
                if (e.key === "Enter") {
                  console.log("creating folder with name:", newFolderName);
                  if (newFolderName.trim()) {
                    handleCreateFolder();
                  }
                  isCreatingFolder = false; // close input on enter
                } else if (e.key === "Escape") {
                  isCreatingFolder = false;
                  newFolderName = "";
                }
              }}
            />
          {:else}
            + new folder
          {/if}
        </button>
      </folders>

      <!-- bookmarks list for the selected folder -->
      <div class="flex flex-col gap-1 overflow-y-auto">
        {#if displayedBookmarks.length > 0}
          {#each displayedBookmarks as bookmark (bookmark.id)}
            <Bookmark
              {bookmark}
              editing={editingBookmarks}
              onDelete={handleDelete}
              onEditTitle={handleEditTitle}
              onEditUrl={handleEditUrl}
            />
          {/each}
        {:else if searchInputValue.trim() !== ""}
          <p
            class="text-gray-500 px-1 font-medium font-geist-mono motion-preset-blur-up-sm"
          >
            no bookmarks match your search in this folder.
          </p>
        {:else}
          <p
            class="text-gray-500 font-medium font-geist-mono px-1 flex items-center gap-2 motion-preset-blur-up-sm"
          >
            no bookmarks
          </p>
        {/if}
      </div>
    </div>
  {/if}
</main>
