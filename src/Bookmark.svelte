<script lang="ts">
  import { Pencil, X } from "lucide-svelte";
  import { onMount, tick } from "svelte";
  import { on } from "svelte/events";

  let {
    bookmark,
    editing = false,
    onDelete = () => {},
    onEdit = (id: string, newTitle: string) => {},
  } = $props();

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

  let id: string = bookmark.id;
  let dominantColor: string = bookmark.faviconColor || "black";

  let holdingOptionKey = $state(false);
  let hoveringBookmark = $state(false);
  let editingTitle = $state(false);
  let newTitle = $state(bookmark.title); // initialize with current title
  let titleEditingElement = $state<HTMLInputElement | null>(null);

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
    if (editingTitle) return; // prevent re-entry

    newTitle = bookmark.title; // resrt input value to current title
    editingTitle = true;
    await tick(); // wait for DOM update

    titleEditingElement?.focus(); // use optional chaining for safety
    titleEditingElement?.select(); // select text for easy editing

    // remove previous listeners if any (safety net)
    cleanupEditKeyListeners?.();

    // add listeners for Enter/Escape/Blur specific to editing mode
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter") {
        event.preventDefault(); // prevent potential form submission
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

    // the cleanup function
    cleanupEditKeyListeners = () => {
      unbindKeyDown();
      unbindBlur();
      cleanupEditKeyListeners = null; // clear reference after cleanup
    };
  }

  function cancelEdit() {
    editingTitle = false;
    cleanupEditKeyListeners?.(); // clean up listeners
  }

  function submitEdit() {
    if (!editingTitle) return; // prevent submit if not editing

    const newTitleTrimmed = newTitle.trim();
    if (newTitleTrimmed && newTitleTrimmed !== bookmark.title) {
      onEdit(id, newTitleTrimmed);
    }
    editingTitle = false;
    cleanupEditKeyListeners?.();
  }
</script>

<bookmark
  class="flex items-center px-0.5 group"
  onmouseenter={() => (hoveringBookmark = true)}
  onmouseleave={() => (hoveringBookmark = false)}
  onfocusin={() => (hoveringBookmark = true)}
  onfocusout={() => (hoveringBookmark = false)}
  role="button"
  tabindex="0"
>
  <div
    class="color-dot mr-2.5"
    style="background-color: {dominantColor};"
    title={stripProtocol(bookmark.url)}
  ></div>

  {#if editingTitle}
    <input
      type="text"
      bind:value={newTitle}
      bind:this={titleEditingElement}
      class="flex-auto font-[450] bg-transparent outline-none ring-1 ring-gray-300 focus:ring-blue-500 rounded px-0.5 mr-auto"
      aria-label="Edit bookmark title"
      onclick={(e) => {
        e.stopPropagation();
      }}
    />
  {:else}
    <a
      href={bookmark.url}
      class="flex-auto font-[450] px-0.5 mr-auto truncate outline-none"
      onclick={(e) => {
        if (holdingOptionKey) {
          e.preventDefault();
          e.stopPropagation();
          startEdit();
        }
      }}
      tabindex="-1"
    >
      {bookmark.title}
    </a>
  {/if}

  <div class="font-mono text-sm ml-2 flex-shrink-0 hidden sm:inline">
    <span class="text-gray-500">[{stripProtocol(bookmark.url)}]</span>
    <span class="text-gray-400 font-semibold ml-2">
      {formatUkDate(bookmark.created_at)}
    </span>
  </div>

  {#if editing || (holdingOptionKey && hoveringBookmark)}
    <div class="flex items-center gap-1 ml-2 flex-shrink-0 pl-1">
      <button
        title="Edit bookmark"
        onclick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          startEdit();
        }}
        class="text-gray-500 hover:text-gray-700 border border-transparent hover:border-gray-300 p-1 rounded"
        aria-label="Edit bookmark"
      >
        <Pencil size={14} />
      </button>
      <button
        title="Delete bookmark"
        onmousedown={(e) => {
          // use mousedown to fire before potential blur
          e.stopPropagation();
          e.preventDefault();
          onDelete(id);
        }}
        class="text-red-500 hover:text-red-700 border border-transparent hover:border-gray-300 p-1 rounded"
        aria-label="Delete bookmark"
      >
        <X size={14} />
      </button>
    </div>
  {/if}
</bookmark>

<style>
  .color-dot {
    width: 13px;
    height: 13px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
  }
  bookmark:focus {
    outline: none;
  }
  bookmark:focus-visible {
    outline: 2px solid blue;
    outline-offset: 2px;
    border-radius: 4px;
  }
</style>
