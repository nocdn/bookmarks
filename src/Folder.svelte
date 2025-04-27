<script lang="ts">
  import { Folder as FolderIcon } from "lucide-svelte";
  let {
    folder,
    currentSelectedFolderId,
    dragOverFolderId,
    handleDragOver,
    handleDrop,
    handleFolderDragEnter,
    handleFolderDragLeave,
    selectFolder,
  } = $props();
</script>

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
  onmousedown={() => selectFolder(folder.id)}
  ><FolderIcon size={16} strokeWidth={2.75} />
  {folder.name}</button
>
