<script lang="ts">
  import { Check, X } from "lucide-svelte";
  import FolderIcon from "./FolderIcon.svelte";
  import { onMount } from "svelte";
  let {
    folder,
    currentSelectedFolderId,
    dragOverFolderId,
    handleDragOver,
    handleDrop,
    handleFolderDragEnter,
    handleFolderDragLeave,
    selectFolder,
    onDeleteFolder = (id: number) => {},
  } = $props();

  let isAltDown = $state(false);
  let isHovering = $state(false);
  let showingDeleteFolder = $derived(isAltDown && isHovering);
  let showingDeleteConfirmation = $state(false);

  onMount(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "Alt") isAltDown = true;
    };
    const up = (e: KeyboardEvent) => {
      if (e.key === "Alt") isAltDown = false;
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  });

  $effect(() => {
    if (!showingDeleteFolder) {
      showingDeleteConfirmation = false;
    }
  });

  function mouseenter() {
    isHovering = true;
  }

  function mouseleave() {
    isHovering = false;
  }
</script>

<div
  id="folder-{folder.id}"
  role="button"
  tabindex="0"
  class="{currentSelectedFolderId === folder.id
    ? 'opacity-100'
    : ''} opacity-60 flex items-center gap-2 p-1.5 px-2.5 w-full text-left cursor-pointer transition-opacity"
  ondragover={handleDragOver}
  ondrop={(e) => handleDrop(e, folder.id)}
  ondragenter={() => handleFolderDragEnter(folder.id)}
  ondragleave={handleFolderDragLeave}
  class:bg-blue-50={dragOverFolderId === folder.id}
  style="color: {folder.color || 'inherit'};"
  onmousedown={() => selectFolder(folder.id)}
  onmouseenter={mouseenter}
  onmouseleave={mouseleave}
>
  <FolderIcon
    fillColor={currentSelectedFolderId === folder.id ? "#F0F0F0" : "none"}
  />
  {folder.name}
  <button class="ml-auto inline-flex items-center gap-0.5">
    <Check
      size={14}
      color="blue"
      strokeWidth={2.5}
      class="{showingDeleteConfirmation
        ? 'opacity-100'
        : 'opacity-0'} transition-opacity"
      onmousedown={(e) => {
        e.stopPropagation();
        e.preventDefault();
        onDeleteFolder(folder.id);
      }}
    />
    <X
      size={14}
      color="red"
      onmousedown={(e) => {
        e.stopPropagation();
        e.preventDefault();
        showingDeleteConfirmation = !showingDeleteConfirmation;
      }}
      class="{showingDeleteFolder
        ? 'opacity-100'
        : 'opacity-0'} transition-opacity"
    /></button
  >
</div>
