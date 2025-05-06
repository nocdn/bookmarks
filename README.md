# bookmarks

> my bookmarks manager, built with svelte, supabase, gemini, and served with caddy

##### setup

1. clone the repo

```bash
git clone https://github.com/yourusername/bookmarks.git
```

2. copy `.env.example` to `.env` and set the environment variables

```bash
cp .env.example .env
```

3. start the containers

```bash
docker compose up -d --build
```

##### usage

open the app in your browser by navigating to `http://localhost:6731` (or the ip address of the host machine, and the port you set in the `.env` file)

##### notes

apologies for such simple documentation, for now, this is just a personal project, without plans to publish it.
