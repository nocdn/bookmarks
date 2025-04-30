<script lang="ts">
  import { X } from "lucide-svelte";
  import { onMount, tick } from "svelte";
  import { on } from "svelte/events";
  import EditIcon from "./EditIcon.svelte";

  let {
    bookmark,
    editing = false,
    onDelete = (id: number) => {},
    onEditTitle = (id: number, newTitle: string) => {},
    onEditUrl = (id: number, newUrl: string) => {},
    onEditBookmark = (id: number, newTitle: string, newUrl: string) => {},
  } = $props<{
    bookmark: {
      id: number;
      url: string;
      title: string;
      created_at: string;
    };
    editing?: boolean;
    onDelete?: (id: number) => void;
    onEditTitle?: (id: number, newTitle: string) => void;
    onEditUrl?: (id: number, newUrl: string) => void;
    onEditBookmark?: (id: number, newTitle: string, newUrl: string) => void;
  }>();

  function getOrdinal(day: number): string {
    if (day > 3 && day < 21) return day + "th";
    switch (day % 10) {
      case 1:
        return day + "st";
      case 2:
        return day + "nd";
      case 3:
        return day + "rd";
      default:
        return day + "th";
    }
  }
  function formatUkDate(dateString: string): string {
    if (!dateString) return "";
    try {
      const date = new Date(dateString);
      const day = date.getDate();
      const dayOrdinal = getOrdinal(day);
      const monthName = date.toLocaleString("en-GB", { month: "long" });
      const year = date.getFullYear();
      return `${dayOrdinal} ${monthName} ${year}`;
    } catch (e) {
      console.error("Error formatting date:", e);
      return "Invalid Date";
    }
  }
  function stripProtocol(url: string): string {
    return url.replace(/^https?:\/\//, "");
  }

  function getDomain(url: string): string {
    try {
      const parsedUrl = new URL(url);
      return parsedUrl.hostname;
    } catch (e) {
      console.warn("Could not parse URL for domain:", url, e);
      const domainMatch = url.match(
        /^(?:https?:\/\/)?(?:[^@\n]+@)?(?:www\.)?([^:\/\n?]+)/im
      );
      return domainMatch ? domainMatch[1] : "";
    }
  }

  let id: number = bookmark.id;
  let holdingOptionKey = $state(false);
  let hoveringBookmark = $state(false);
  let newTitle = $state(bookmark.title);
  let titleEditingElement = $state<HTMLInputElement | null>(null);
  let isDragging = $state(false);

  let isEditing = $state(false);

  let cleanupEditKeyListeners: (() => void) | null = null;

  onMount(() => {
    const keydownHandler = (event: KeyboardEvent) => {
      if (event.key === "Alt") {
        event.preventDefault();
        holdingOptionKey = true;
      }
    };
    const keyupHandler = (event: KeyboardEvent) => {
      if (event.key === "Alt") {
        event.preventDefault();
        holdingOptionKey = false;
      }
    };

    const unbindKeydown = on(window, "keydown", keydownHandler);
    const unbindKeyup = on(window, "keyup", keyupHandler);

    return () => {
      unbindKeydown();
      unbindKeyup();
    };
  });

  function cancelEdit() {
    isEditing = false;
    newTitle = bookmark.title;
    newUrl = bookmark.url;
    cleanupEditKeyListeners?.();
  }

  let newUrl = $state(bookmark.url);
  let urlEditingElement = $state<HTMLInputElement | null>(null);

  function submitBookmarkEdit() {
    const newUrlTrimmed = newUrl.trim();
    const newTitleTrimmed = newTitle.trim();
    onEditBookmark(id, newTitleTrimmed, newUrlTrimmed);
    isEditing = false;
    cleanupEditKeyListeners?.();
  }

  function handleDragStart(event: DragEvent) {
    if (isEditing) {
      event.preventDefault();
      return;
    }
    if (event.dataTransfer) {
      event.dataTransfer.setData("text/plain", id.toString());
      event.dataTransfer.effectAllowed = "move";
      isDragging = true;
    }
  }

  function handleDragEnd() {
    isDragging = false;
  }

  function formatDate(dateString: string): string {
    if (!dateString) return "";
    try {
      const date = new Date(dateString);
      const day = date.getDate();
      const dayOrdinal = getOrdinal(day);
      const monthName = date.toLocaleString("en-GB", { month: "long" });
      const year = date.getFullYear();
      return `${dayOrdinal} ${monthName} ${year}`;
    } catch (e) {
      console.error("Error formatting date:", e);
      return "Invalid Date";
    }
  }
</script>

{#if isEditing}
  <editing class="p-3 flex flex-col gap-2 border border-slate-200 mb-3">
    <div class="group">
      <p
        class="text-sm font-jetbrains-mono font-medium text-gray-500 group-focus-within:text-blue-500"
      >
        TITLE
      </p>
      <input
        type="text"
        bind:value={newTitle}
        class="w-full p-0 focus:outline-none"
        bind:this={titleEditingElement}
        placeholder="Edit title"
        autocomplete="off"
        onkeydown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            urlEditingElement?.focus();
          } else if (e.key === "Escape") {
            cancelEdit();
          }
        }}
      />
    </div>
    <div class="group">
      <p
        class="text-sm font-jetbrains-mono text-gray-500 font-medium group-focus-within:text-blue-500"
      >
        LINK
      </p>
      <input
        type="text"
        bind:value={newUrl}
        class="w-full focus:outline-none"
        bind:this={urlEditingElement}
        placeholder="Edit link"
        autocomplete="off"
        onkeydown={(e) => {
          if (e.key === "Enter") {
            console.log("enter pressed in url edit");
            e.preventDefault();
            submitBookmarkEdit();
          } else if (e.key === "Escape") {
            cancelEdit();
          }
        }}
      />
    </div>
    <div class="flex items-end">
      <p class="text-xs text-gray-400 mb-0.5">
        {formatDate(bookmark.updated_at)}
      </p>
      <button
        class="text-red-900 px-3 py-1 border border-gray-200 hover:border-red-500/30 text-sm cursor-pointer ml-auto"
        onclick={cancelEdit}
      >
        CANCEL
      </button>
      <button
        class="text-blue-800 px-3.5 py-1 border border-gray-200 hover:border-blue-500/40 text-sm cursor-pointer ml-2"
        onclick={submitBookmarkEdit}
      >
        SAVE
      </button>
    </div>
  </editing>
{:else}
  <bookmark
    class="flex items-center px-0.5 group max-w-full transition-opacity duration-150 {isDragging
      ? 'opacity-50'
      : ''} font-geist-mono font-medium motion-preset-blur-up-sm overflow-hidden"
    onmouseenter={() => (hoveringBookmark = true)}
    onmouseleave={() => (hoveringBookmark = false)}
    onfocusin={() => (hoveringBookmark = true)}
    onfocusout={() => (hoveringBookmark = false)}
    role="button"
    tabindex="0"
    draggable="true"
    ondragstart={handleDragStart}
    ondragend={handleDragEnd}
  >
    <div id="img-title" class="flex items-center flex-shrink-0">
      <img
        src={`https://www.google.com/s2/favicons?domain=${getDomain(bookmark.url)}&sz=32`}
        alt=""
        class="favicon mr-2 flex-shrink-0 mb-0.5"
        width="14"
        height="14"
        loading="lazy"
        title={stripProtocol(bookmark.url)}
      />

      <a
        href={bookmark.url}
        class="flex-grow flex-shrink min-w-0 max-w-full truncate font-[450] px-0.5 mr-auto outline-none {holdingOptionKey
          ? 'cursor-text'
          : ''}"
        onclick={(e) => {
          if (holdingOptionKey) {
            e.preventDefault();
            e.stopPropagation();
          }
        }}
        onmousedown={(e) => {
          if (holdingOptionKey) {
            e.stopPropagation();
            e.preventDefault();
          }
        }}
        tabindex="-1"
        title={bookmark.title}
      >
        {bookmark.title}
      </a>
    </div>

    <div class="ml-auto flex items-center mr-1 gap-1.5">
      <button
        tabindex="0"
        id="delete-icon"
        class="opacity-0 {holdingOptionKey && hoveringBookmark
          ? 'opacity-100'
          : ''} transition-opacity cursor-pointer"
        onclick={() => {
          onDelete(bookmark.id);
        }}
      >
        <X size={16} strokeWidth={2.5} color="red" />
      </button>
      <button
        tabindex="0"
        id="edit-icon"
        class="opacity-45 hover:opacity-100 transition-opacity cursor-pointer"
        onclick={() => {
          isEditing = true;
          tick().then(() => {
            titleEditingElement?.focus();
            titleEditingElement?.select();
          });
        }}
      >
        <EditIcon />
      </button>
    </div>

    <div id="url-date" class="flex items-center">
      <p
        class="text-gray-400 w-fit font-semibold ml-2 flex-shrink-0 whitespace-nowrap"
      >
        {formatUkDate(bookmark.created_at)}
      </p>
    </div>
  </bookmark>
{/if}

<style>
  .favicon {
    width: 15px;
    height: 15px;
    display: inline-block;
    object-fit: contain;
    vertical-align: middle;
    border-radius: 3px;
  }
  bookmark[draggable="true"] {
    cursor: grab;
  }
  bookmark[draggable="true"]:active {
    cursor: grabbing;
  }
</style>
