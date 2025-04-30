<script lang="ts">
  import GithubIcon from "./GithubIcon.svelte";
  import { onMount } from "svelte";
  let { onclick = () => {} } = $props<{
    onclick?: () => void;
  }>();
</script>

<button
  id="folder-github"
  tabindex="0"
  class="flex items-center gap-2 p-1.5 px-2.5 w-full text-left cursor-pointer transition-opacity"
  {onclick}
>
  <GithubIcon /> Github Stars
</button>
