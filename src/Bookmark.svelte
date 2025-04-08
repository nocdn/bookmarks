<script lang="ts">
  import { Pencil, X } from "lucide-svelte";
  import { onMount } from "svelte";

  let {
    favicon = null,
    bookmark,
    editing = false,
    onDelete = () => {},
    onEdit = () => {},
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
      // Example format: 4th April 2025
      return `${dayOrdinal} ${monthName} ${year}`;
    } catch (e) {
      console.error("Error formatting date:", e);
      return "Invalid Date";
    }
  }

  function stripProtocol(url: string): string {
    return url.replace(/^https?:\/\//, "");
  }

  function getFaviconUrl(url: string): string {
    // Extract domain from URL
    const domain = stripProtocol(url).split("/")[0];
    // Use Google's favicon service
    return `https://www.google.com/s2/favicons?domain=${domain}`;
  }

  let id: string = bookmark.id;
  console.log(id);
</script>

<bookmark class="flex items-center px-0.5">
  <a href={bookmark.url} class="flex items-center gap-2 mr-auto font-[450]">
    <img
      src={getFaviconUrl(bookmark.url)}
      alt="favicon"
      width="14"
      height="14"
      class="inline-block"
    />
    {bookmark.title}
  </a>
  <div class="font-mono">
    <span>[{stripProtocol(bookmark.url)}]</span>
    <span class="text-gray-400 font-semibold">
      {formatUkDate(bookmark.created_at)}
    </span>
  </div>
  {#if editing}
    <div class="flex items-center gap-2 ml-4">
      <button
        title="Edit bookmark"
        class="text-gray-500 hover:text-gray-700 border border-gray-300 p-1 hover:border-gray-400"
      >
        <Pencil size={14} />
      </button>
      <button
        title="Delete bookmark"
        onmousedown={() => {
          onDelete(id);
        }}
        class="text-red-500 hover:text-red-700 border border-gray-300 p-1 hover:border-gray-400"
      >
        <X size={14} />
      </button>
    </div>
  {/if}
</bookmark>
