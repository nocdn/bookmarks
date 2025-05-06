<script lang="ts">
  import TwitterIcon from "./TwitterIcon.svelte";
  import { onMount } from "svelte";
  let { onclick = () => {} } = $props<{
    onclick?: () => void;
  }>();
</script>

<button
  id="folder-twitter"
  tabindex="0"
  class="flex items-center gap-2 p-1.5 px-2.5 w-full text-left cursor-pointer transition-opacity"
  {onclick}
>
  <TwitterIcon /> Twitter Saved
</button>
