<script lang="ts">
  import {
    ArrowRight,
    PlusCircle,
    Search,
    Folder as FolderIcon,
    Inbox,
    HeartCrack,
    Sparkles,
    Command,
  } from "lucide-svelte";
  import Bookmark from "./Bookmark.svelte";
  import Folder from "./Folder.svelte";
  import { onMount, tick } from "svelte";
  import { createClient } from "@supabase/supabase-js";
  import GithubFolder from "./GithubFolder.svelte";
  import GithubStar from "./GithubStar.svelte";
  import TwitterFolder from "./TwitterFolder.svelte";
  import Spinner from "./Spinner.svelte";

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

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    console.error(
      "Supabase URL or Anon Key is not configured. Check your environment variables."
    );
  }

  const supabase = createClient(supabaseUrl!, supabaseAnonKey!);

  let searchInputElement: HTMLInputElement | null = $state(null);
  let newFolderNameElement: HTMLInputElement | null = $state(null);
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
  let duplicateFolderError = $state(false);
  let expandedFolderIds: Array<number> = $state([]);
  let showingFolderCreationHint: boolean = $state(false);

  function decodeHtmlEntities(text: string): string {
    if (typeof document !== "undefined") {
      const textarea = document.createElement("textarea");
      textarea.innerHTML = text;
      return textarea.value;
    }
    return text;
  }

  function saveLastBookmarkId(id: number) {
    localStorage.setItem("lastBookmarkId", id.toString());
  }
  function getLastBookmarkId(): number | null {
    const lastBookmarkId = localStorage.getItem("lastBookmarkId");
    return lastBookmarkId ? parseInt(lastBookmarkId, 10) : null;
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
        if (Array.isArray(faviconColor) && faviconColor.length >= 3) {
          faviconRgbCodeString = `rgb(${faviconColor[0]}, ${faviconColor[1]}, ${faviconColor[2]})`;
        } else {
          faviconRgbCodeString = "rgb(0, 0, 0)";
        }
      } catch (fetchError: any) {
        console.warn("could not fetch or process page title:", fetchError);
        createError = `could not get title: ${fetchError.message}`;
        pageTitle = url.replace(/^https?:\/\//, "").replace(/^www\./, "");
        if (pageTitle.endsWith("/")) pageTitle = pageTitle.slice(0, -1);
        faviconRgbCodeString = "rgb(0, 0, 0)";
      }
      const folderId = await getLLMfolder(url);
      const { data: newBookmarkData, error: insertError } = await supabase
        .from("bookmarks")
        .insert([
          {
            url: url,
            title: pageTitle || "Untitled",
            faviconColor: faviconRgbCodeString,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            folder_id: folderId,
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
      } else {
        const value = searchInputValue.trim();
        if (value) {
          createBookmark(value);
        }
      }
    }
    if (event.key === "Enter" && event.altKey) {
      event.preventDefault();
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

  let searchedBookmarks = $derived(
    bookmarks.filter(
      (b) =>
        fuzzyMatch(b.title || "", searchInputValue) ||
        fuzzyMatch(b.url, searchInputValue)
    )
  );

  let displayedBookmarks = $derived(
    searchedBookmarks.filter((b) => b.folder_id === currentSelectedFolderId)
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
    fetchFolders();
    currentSelectedFolderId = getLastBookmarkId();
    return () => {
      document.removeEventListener("keydown", handleGlobalKeydown);
    };
  });

  async function handleEditBookmark(
    id: number,
    newTitle: string,
    newUrl: string
  ) {
    const originalBookmarks = [...bookmarks];
    bookmarks = bookmarks.map((b) => {
      if (b.id === id) {
        return {
          ...b,
          title: newTitle,
          url: newUrl,
          updated_at: new Date().toISOString(),
        };
      }
      return b;
    });
    try {
      const { error } = await supabase
        .from("bookmarks")
        .update({
          title: newTitle,
          url: newUrl,
          updated_at: new Date().toISOString(),
        })
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
    const currentTarget = event.currentTarget as HTMLElement;
    const relatedTarget = event.relatedTarget as Node;
    if (!relatedTarget || !currentTarget.contains(relatedTarget)) {
      dragOverFolderId = null;
    }
  }

  $effect(() => {
    if (bookmarks.length === 0) {
      editingBookmarks = false;
    }
  });

  async function openNewFolderInput() {
    isCreatingFolder = true;
    setTimeout(() => {
      newFolderNameElement?.focus();
    }, 10);
    showingFolderCreationHint = true;
  }

  async function handleCreateFolder(forceRoot: boolean = false) {
    isCreatingFolder = false;
    const parentId = forceRoot ? null : currentSelectedFolderId;
    const { data: newFolderData, error: insertError } = await supabase
      .from("folders")
      .insert([
        {
          name: newFolderName,
          color: newFolderColor,
          parent_id: parentId,
        },
      ]);
    if (insertError) {
      if (insertError.code === "23505") {
        duplicateFolderError = true;
        newFolderName = "";
        setTimeout(() => {
          duplicateFolderError = false;
        }, 1000);
      }
      return;
    }
    newFolderName = "";
    fetchFolders();
  }

  async function getLLMfolder(link: string) {
    const response = await fetch(
      `/api/gemini/${link.replace(/^https?:\/\//, "")}`
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
    return parseInt(data);
  }

  function selectFolder(id: number) {
    isShowingGithubStars = false;
    currentSelectedFolderId = id;
    saveLastBookmarkId(id);
    expandedFolderIds = [];
  }

  function toggleFolderExpand(id: number) {
    if (expandedFolderIds.includes(id)) {
      expandedFolderIds = expandedFolderIds.filter((fid) => fid !== id);
    } else {
      expandedFolderIds = [...expandedFolderIds, id];
    }
  }

  async function handleDeleteFolder(id: number) {
    const originalFolders = [...folders];
    folders = folders.filter((f) => f.id !== id);
    try {
      const { error } = await supabase.from("folders").delete().match({ id });
      if (error) {
        folders = originalFolders;
      }
    } catch (error: any) {
      folders = originalFolders;
    }
  }

  let isShowingGithubStars = $state(false);
  let githubStars: Array<any> = $state([]);
  let isFetchingGithubStars = $state(false);
  function fetchGithubStars() {
    isShowingGithubStars = !isShowingGithubStars;
    isFetchingGithubStars = true;
    fetch("https://api.github.com/users/nocdn/starred")
      .then((response) => response.json())
      .then((data) => {
        githubStars = data;
        isFetchingGithubStars = false;
      })
      .catch((error) => {
        console.error("Error fetching Github stars:", error);
      });
  }

  let isShowingTwitterBookmarks = $state(false);
  let isFetchingTwitterBookmarks = $state(false);

  async function downloadExport() {
    const response = await fetch("/api/export");

    if (!response.ok) {
      console.error("Error fetching export:", response.statusText);
      return;
    }

    const blob = await response.blob();

    const now = new Date();

    const day = String(now.getDate()).padStart(2, "0"); // dd
    const month = String(now.getMonth() + 1).padStart(2, "0"); // mm (getMonth() is 0-indexed)
    const year = now.getFullYear(); // yyyy
    const hours = String(now.getHours()).padStart(2, "0"); // hh
    const minutes = String(now.getMinutes()).padStart(2, "0"); // mm

    const filename = `bookmarks_export_full_${day}_${month}_${year}_${hours}-${minutes}.zip`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;

    document.body.appendChild(a);
    a.click();

    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
</script>

<main
  class="p-6 flex flex-col gap-3 font-jetbrains-mono h-dvh overflow-y-hidden"
>
  <header class="flex gap-2 items-center font-jetbrains-mono flex-shrink-0">
    <ArrowRight size="15" /> BOOKMARKS {#if duplicateFolderError}
      <p
        class="text-red-700 font-medium motion-preset-focus-sm ml-3 animate-error-shake"
      >
        folder already exists
      </p>
    {/if}
    {#if isLoading || isFetchingGithubStars || isFetchingTwitterBookmarks || isCreating}
      <Spinner opacity={60} class="-translate-x-1" />
    {/if}
    <button
      disabled={isCreating}
      onmousedown={() => {
        console.log("exporting bookmarks and folders");
        downloadExport();
      }}
      class="ml-auto border border-gray-200 px-2.5 py-0.5 cursor-pointer hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      EXPORT
    </button>
    <button
      disabled={isCreating}
      onmousedown={() => (isAddingMultiple = !isAddingMultiple)}
      class="border border-gray-200 px-2.5 py-0.5 cursor-pointer hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {#if isAddingMultiple}
        FINISH
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
  </search>

  {#if createError}
    <p class="text-red-500 text-sm mb-2 flex-shrink-0">{createError}</p>
  {/if}
  {#if isLoading}
    <p class="flex-shrink-0 motion-translate-y-out-25 motion-opacity-out-0"></p>
  {:else if fetchError}
    <p class="text-red-600 flex-shrink-0">
      Error loading bookmarks: {fetchError}
    </p>
  {:else if bookmarks.length === 0 && !isCreating}
    <p class="text-gray-400 font-[450] flex-shrink-0">
      No bookmarks found. Paste a URL and press Enter to add one.
    </p>
  {:else}
    <div
      id="separated"
      class="grid grid-cols-[auto_1fr] gap-6 flex-grow min-h-0"
    >
      <folders
        class="flex flex-col gap-1 font-medium flex-shrink-0 pr-4 motion-preset-blur-up-sm min-h-0"
      >
        <button
          id="folder-uncategorized"
          class="{currentSelectedFolderId === null
            ? 'font-semibold opacity-100'
            : ''} opacity-50 flex items-center gap-2 p-1.5 px-2.5 w-full text-left cursor-pointer transition-opacity flex-shrink-0"
          ondragover={handleDragOver}
          ondrop={(e) => handleDrop(e, null)}
          ondragenter={() => handleFolderDragEnter("uncategorized")}
          ondragleave={handleFolderDragLeave}
          class:bg-blue-50={dragOverFolderId === "uncategorized"}
          onmousedown={() => {
            isShowingGithubStars = false;
            isShowingTwitterBookmarks = false;
            currentSelectedFolderId = null;
            expandedFolderIds = [];
          }}
        >
          <Inbox
            size={16}
            strokeWidth={currentSelectedFolderId === null ? 3 : 2.5}
            class="text-gray-600"
          />
          Uncategorized
        </button>

        <div
          class="flex-grow overflow-y-auto min-h-0 py-1"
          style="scrollbar-width: thin; scrollbar-color: #F2F2F2 white; padding-bottom: 1.5rem;"
        >
          {#each folders.filter((f) => f.parent_id === null) as folder (folder.id)}
            <Folder
              {folder}
              {currentSelectedFolderId}
              {dragOverFolderId}
              {handleDragOver}
              {handleDrop}
              {handleFolderDragEnter}
              {handleFolderDragLeave}
              {selectFolder}
              onDeleteFolder={handleDeleteFolder}
              allFolders={folders}
              {expandedFolderIds}
              {toggleFolderExpand}
              level={0}
            />
          {/each}
        </div>

        <button
          id="new-folder"
          class="mr-auto p-1.5 px-2.5 pl-[12.5px] text-gray-500 rounded-md flex items-center gap-2 cursor-pointer flex-shrink-0 relative"
          onmousedown={() => {
            openNewFolderInput();
          }}
        >
          <div
            id="new-folder-gradient"
            class="absolute w-58 bottom-8 left-0 right-0 h-12 bg-gradient-to-t from-white via-white to-transparent pointer-events-none"
            style="width: {newFolderNameElement?.clientWidth}px;"
          ></div>
          {#if isCreatingFolder}
            <div class="flex flex-col gap-2 motion-preset-blur-up-sm">
              <div class="flex flex-col gap-2 mb-1.5">
                <div class="flex items-center gap-2">
                  <Command
                    size={10}
                    strokeWidth={2.5}
                    class="text-gray-600 bg-gray-100 rounded-sm p-1 w-5 h-5"
                  /> +
                  <div
                    class="text-xs text-gray-600 font-jetbrains-mono rounded-sm bg-gray-100 px-1 py-0.5"
                  >
                    ENTER
                  </div>
                  <p class="text-xs inline-flex items-center font-medium">
                    <ArrowRight size={12} strokeWidth={2.5} class="mr-2" /> root
                  </p>
                </div>

                <div class="flex items-center gap-2">
                  <div
                    class="text-xs text-gray-600 font-jetbrains-mono rounded-sm bg-gray-100 px-1 py-0.5"
                  >
                    ENTER
                  </div>
                  <p class="text-xs inline-flex items-center font-medium">
                    <ArrowRight size={12} strokeWidth={2.5} class="mr-2" /> nested
                  </p>
                </div>
              </div>
              <input
                type="text"
                class="w-[80%] focus:outline-none font-medium font-geist-mono bg-blue-50/50 placeholder:text-blue-600/60 p-1 px-[7px] -translate-x-1 text-black"
                placeholder="new folder name"
                bind:value={newFolderName}
                bind:this={newFolderNameElement}
                onkeydown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    if (newFolderName.trim()) {
                      handleCreateFolder(e.metaKey || e.ctrlKey);
                    }
                    isCreatingFolder = false;
                  } else if (e.key === "Escape") {
                    isCreatingFolder = false;
                    newFolderName = "";
                  }
                }}
                onfocus={() => {
                  newFolderNameElement?.select();
                }}
                onblur={() => {
                  isCreatingFolder = false;
                  newFolderName = "";
                }}
              />
            </div>
          {:else}
            <p class="motion-preset-blur-up-sm">+ new folder</p>
          {/if}
        </button>
        <div class="mt-auto flex-shrink-0">
          <TwitterFolder
            onclick={() => {
              isShowingGithubStars = false;
              isShowingTwitterBookmarks = true;
            }}
          />
          <GithubFolder onclick={fetchGithubStars} />
        </div>
      </folders>

      {#if isShowingGithubStars}
        <div
          id="github-stars"
          class="max-w-full flex flex-col gap-2 overflow-y-scroll"
        >
          {#each githubStars as star (star.id)}
            <GithubStar starData={star} />
          {/each}
        </div>
      {:else if isShowingTwitterBookmarks}
        <p class="text-gray-500 font-bold">🚧 WORK IN PROGRESS</p>
      {:else}
        <div
          id="bookmarks"
          class="flex flex-col gap-2 overflow-y-auto pt-[4px]"
        >
          {#if displayedBookmarks.length > 0}
            {#each displayedBookmarks as bookmark (bookmark.id)}
              <Bookmark
                {bookmark}
                editing={editingBookmarks}
                onDelete={handleDelete}
                onEditBookmark={handleEditBookmark}
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
      {/if}
    </div>
  {/if}
</main>
