# Confluence Actions

Loaded on demand by the `confluence` procedure. Each action is a
`python3` call against the Confluence REST API using the Jira credentials.

## Actions

### 1. Get Page (view)

Trigger: `$ARGUMENTS` contains `get`, `show`, `view` followed by a page ID, or just a numeric ID.

```
GET /pages/{id}?body-format=storage&include-labels=true&include-version=true
```

Display:
- ID, title, status, space ID, parent ID
- Version number, author, created date
- Labels
- Body content (render from storage format)
- Links (webui URL)

### 2. Create Page

Trigger: `$ARGUMENTS` contains `create` or `new`.

1. Ask the user for: title, space ID (or space key to resolve), parent page ID (optional), content body
2. Create the page:

```
POST /pages
{
  "spaceId": "<space_id>",
  "status": "current",
  "title": "<title>",
  "parentId": "<parent_id>",       // optional
  "body": {
    "representation": "storage",
    "value": "<html_content>"
  }
}
```

3. Display the created page ID and webui link from the response.

### 3. Update Page

Trigger: `$ARGUMENTS` contains `update` or `edit` followed by a page ID.

1. Fetch the current page to get the version number:
   ```
   GET /pages/{id}?include-version=true
   ```
2. Ask the user for new content (or use provided text)
3. For edits based on an earlier fetch, re-fetch immediately before the write and compare the
   current storage body with the reviewed body. Confluence may omit a trailing newline when it
   returns storage content, so normalize only trailing whitespace (for example, `rstrip()`) before
   comparison. Abort and rebase if any substantive content differs.
4. Update:

```
PUT /pages/{id}
{
  "id": "<page_id>",
  "status": "current",
  "title": "<title>",
  "body": {
    "representation": "storage",
    "value": "<new_html_content>"
  },
  "version": {
    "number": <current_version + 1>,
    "message": "Updated via GXS plugin"
  }
}
```

**Important**: The version number must be incremented from the current version.

5. Use the CLI `update` command with mandatory `--expected-body-file` and `--verify`. It performs
   the strict optimistic-concurrency comparison before the PUT and guarded semantic storage
   readback after it. Its normalizer preserves CDATA, plain-text, `pre`, and `code` payload bytes;
   do not reimplement the comparison in an ad hoc script.

### 4. Delete Page

Trigger: `$ARGUMENTS` contains `delete` or `remove` followed by a page ID.

**Confirm with the user before deleting.**

```
DELETE /pages/{id}
```

Moves page to trash. To permanently delete a trashed page:
```
DELETE /pages/{id}?purge=true
```

To delete a draft:
```
DELETE /pages/{id}?draft=true
```

### 5. Search / List Pages

Trigger: `$ARGUMENTS` contains `search`, `find`, or `list`.

```
GET /pages?title=<query>&limit=25&body-format=view
```

Optional filters:
- `space-id=<id>` — filter by space
- `status=current` — only published pages
- `sort=-created-at` — sort by newest first

Display results as a table: ID | Title | Status | Space ID | Created

For pagination, check `response["_links"]["next"]` for the cursor.

### 6. List Pages in Space

Trigger: `$ARGUMENTS` contains `space` followed by a space ID or key.

If a space key (string) is given, first resolve to space ID:
```
GET /spaces?keys=<space_key>
```

Then list pages:
```
GET /spaces/{id}/pages?limit=25&body-format=view
```

Optional: `depth=root` for top-level only, `sort=-created-at`, `title=<filter>`.

### 7. Update Page Title

Trigger: `$ARGUMENTS` contains `title` or `rename` followed by a page ID.

```
PUT /pages/{id}/title
{
  "status": "current",
  "title": "<new_title>"
}
```

### 8. Get Pages for Label

Trigger: `$ARGUMENTS` contains `label` or `labels` followed by a label ID.

```
GET /labels/{id}/pages?limit=25
```
