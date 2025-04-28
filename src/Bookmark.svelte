<script lang="ts">
  import { X } from "lucide-svelte";
  import { onMount, tick } from "svelte";
  import { on } from "svelte/events";

  let {
    bookmark,
    editing = false,
    onDelete = (id: number) => {},
    onEditTitle = (id: number, newTitle: string) => {},
    onEditUrl = (id: number, newUrl: string) => {},
  } = $props<{
    bookmark: {
      id: number;
      url: string;
      title: string;
      created_at: string;
      // faviconColor?: string; // removed as it's not used for the icon anymore
    };
    editing?: boolean;
    onDelete?: (id: number) => void;
    onEditTitle?: (id: number, newTitle: string) => void;
    onEditUrl?: (id: number, newUrl: string) => void;
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
      // using the built-in url object to easily get the hostname
      const parsedUrl = new URL(url);
      return parsedUrl.hostname;
    } catch (e) {
      console.warn("Could not parse URL for domain:", url, e);
      // fallback if the url is strange - try to extract something that looks like a domain
      const domainMatch = url.match(
        /^(?:https?:\/\/)?(?:[^@\n]+@)?(?:www\.)?([^:\/\n?]+)/im
      );
      return domainMatch ? domainMatch[1] : "";
    }
  }

  let id: number = bookmark.id;
  let holdingOptionKey = $state(false);
  let hoveringBookmark = $state(false);
  let editingTitle = $state(false);
  let newTitle = $state(bookmark.title);
  let titleEditingElement = $state<HTMLInputElement | null>(null);
  let isDragging = $state(false);

  let cleanupEditKeyListeners: (() => void) | null = null;

  onMount(() => {
    const keydownHandler = (event: KeyboardEvent) => {
      if (event.key === "Alt") {
        holdingOptionKey = true;
      }
    };
    const keyupHandler = (event: KeyboardEvent) => {
      if (event.key === "Alt") {
        holdingOptionKey = false;
      }
    };

    const unbindKeydown = on(window, "keydown", keydownHandler);
    const unbindKeyup = on(window, "keyup", keyupHandler);

    return () => {
      unbindKeydown();
      unbindKeyup();
      cleanupEditKeyListeners?.();
    };
  });

  async function startEdit() {
    if (editingTitle || editingUrl) return;

    newTitle = bookmark.title;
    editingTitle = true;
    await tick();

    titleEditingElement?.focus();
    titleEditingElement?.select();

    cleanupEditKeyListeners?.();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitEdit();
      } else if (event.key === "Escape") {
        cancelEdit();
      }
    };

    const handleBlur = () => {
      submitEdit();
    };

    const unbindKeyDown = on(titleEditingElement!, "keydown", handleKeyDown);
    const unbindBlur = on(titleEditingElement!, "blur", handleBlur);

    cleanupEditKeyListeners = () => {
      unbindKeyDown();
      unbindBlur();
      cleanupEditKeyListeners = null;
    };
  }

  function cancelEdit() {
    editingTitle = false;
    editingUrl = false;
    cleanupEditKeyListeners?.();
  }

  function submitEdit() {
    if (!editingTitle) return;

    const newTitleTrimmed = newTitle.trim();
    if (newTitleTrimmed && newTitleTrimmed !== bookmark.title) {
      onEditTitle(id, newTitleTrimmed);
    }
    editingTitle = false;
    cleanupEditKeyListeners?.();
  }

  function submitUrlEdit() {
    if (!editingUrl) return;

    const newUrlTrimmed = newUrl.trim();
    if (newUrlTrimmed && newUrlTrimmed !== bookmark.url) {
      onEditUrl(id, newUrlTrimmed);
    }
    editingUrl = false;
    cleanupEditKeyListeners?.();
  }

  let editingUrl = $state(false);
  let newUrl = $state(bookmark.url);
  let urlEditingElement = $state<HTMLInputElement | null>(null);

  async function startUrlEdit() {
    if (editingUrl || editingTitle) return;

    newUrl = bookmark.url;
    editingUrl = true;
    await tick();

    urlEditingElement?.focus();
    urlEditingElement?.select();

    cleanupEditKeyListeners?.();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitUrlEdit();
      } else if (event.key === "Escape") {
        cancelEdit();
      }
    };

    const handleBlur = () => {
      submitUrlEdit();
    };

    const unbindKeyDown = on(urlEditingElement!, "keydown", handleKeyDown);
    const unbindBlur = on(urlEditingElement!, "blur", handleBlur);

    cleanupEditKeyListeners = () => {
      unbindKeyDown();
      unbindBlur();
      cleanupEditKeyListeners = null;
    };
  }

  let urlEditingFieldWidth = $state(0);
  $effect(() => {
    urlEditingFieldWidth = Math.max(100, newUrl.length * 8.66); // approx width + min width
  });

  function handleDragStart(event: DragEvent) {
    if (editingTitle || editingUrl) {
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
</script>

<bookmark
  class="flex items-center px-0.5 group max-w-full transition-opacity duration-150 {isDragging
    ? 'opacity-50'
    : ''} font-geist-mono font-medium motion-preset-blur-up-sm"
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
  <img
    src={`https://www.google.com/s2/favicons?domain=${getDomain(bookmark.url)}&sz=32`}
    alt=""
    class="favicon mr-2 flex-shrink-0"
    width="14"
    height="14"
    loading="lazy"
    title={stripProtocol(bookmark.url)}
  />

  {#if editingTitle}
    <input
      type="text"
      bind:value={newTitle}
      bind:this={titleEditingElement}
      class="flex-auto font-[450] bg-transparent focus:outline-blue-300 focus:outline-[1.5px] ml-0.5 mr-auto p-0.5"
      aria-label="Edit bookmark title"
      onclick={(e) => {
        e.stopPropagation();
      }}
      onmousedown={(e) => e.stopPropagation()}
      data-1p-ignore
    />
  {:else}
    <a
      href={bookmark.url}
      class="flex-auto font-[450] min-w-fit px-0.5 mr-auto truncate outline-none {holdingOptionKey
        ? 'cursor-text'
        : ''}"
      onclick={(e) => {
        if (holdingOptionKey) {
          e.preventDefault();
          e.stopPropagation();
          startEdit();
        }
      }}
      onmousedown={(e) => {
        if (holdingOptionKey) {
          e.stopPropagation();
          e.preventDefault();
        }
      }}
      tabindex="-1"
    >
      {bookmark.title}
    </a>
  {/if}

  <div class="font-mono text-sm ml-2 flex-shrink-0 hidden sm:inline">
    {#if editingUrl}
      <input
        type="text"
        bind:value={newUrl}
        bind:this={urlEditingElement}
        class="text-gray-500 focus:outline-blue-300 focus:outline-[1.5px] p-0.5"
        style="width: {urlEditingFieldWidth}px;"
        aria-label="Edit bookmark url"
        onclick={(e) => {
          e.stopPropagation();
        }}
        onmousedown={(e) => e.stopPropagation()}
      />
    {:else}
      <span
        role="button"
        tabindex="0"
        class="text-gray-500 px-0.5 outline-none {holdingOptionKey
          ? 'cursor-text'
          : ''}"
        onmousedown={(e) => {
          e.stopPropagation();
          e.preventDefault();
          if (holdingOptionKey) {
            startUrlEdit();
          }
        }}
        onclick={(e) => {
          if (holdingOptionKey) {
            e.preventDefault();
            e.stopPropagation();
            startUrlEdit();
          }
        }}
      >
        [{stripProtocol(bookmark.url)}]
      </span>
    {/if}
    <span class="text-gray-400 font-semibold ml-2">
      {formatUkDate(bookmark.created_at)}
    </span>
  </div>

  {#if editing || (holdingOptionKey && hoveringBookmark)}
    <div class="flex items-center gap-1 ml-2 flex-shrink-0 pl-1">
      <button
        title="Delete bookmark"
        onmousedown={(e) => {
          e.stopPropagation();
          e.preventDefault();
          onDelete(id);
        }}
        class="text-red-500 hover:text-red-700 border border-transparent hover:border-gray-300 p-1 rounded focus:outline-blue-300 focus:outline-[1.5px]"
        aria-label="Delete bookmark"
      >
        <X size={14} />
      </button>
    </div>
  {/if}
</bookmark>

<style>
  /* updated style for the favicon image */
  .favicon {
    width: 15px; /* standard favicon size */
    height: 15px; /* standard favicon size */
    display: inline-block; /* keep it inline */
    object-fit: contain; /* make sure the icon fits nicely */
    vertical-align: middle; /* align nicely with the text */
    border-radius: 3px;
  }
  bookmark[draggable="true"] {
    cursor: grab;
  }
  bookmark[draggable="true"]:active {
    cursor: grabbing;
  }
</style>
