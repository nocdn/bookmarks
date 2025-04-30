<script lang="ts">
  import { Globe, Code } from "lucide-svelte";
  let { starData } = $props<{
    starData: {
      full_name: string;
      homepage: string;
      stargazers_count: number;
      description: string;
    };
  }>();

  let isHovering = $state(false);
</script>

<div
  role="button"
  tabindex="0"
  class="border border-gray-200 px-2.5 py-1.5 flex flex-col gap-1.5 w-full h-fit relative"
  onmouseenter={() => (isHovering = true)}
  onmouseleave={() => (isHovering = false)}
>
  <p class="font-semibold">{starData.full_name}</p>
  <p class="text-xs text-gray-400">{starData.stargazers_count} stars</p>
  <p class="text-sm">{starData.description}</p>
  {#if isHovering}
    <div
      class="bg-white rounded-lg px-2 py-1 flex gap-2 items-center absolute top-2 right-1.5 motion-preset-blur-up-sm"
    >
      <a href={starData.homepage}><Globe size={13} /></a>
      <a href={`https://github.com/${starData.full_name}`}
        ><Code size={15} class="mt-0.25" /></a
      >
    </div>
  {/if}
</div>
