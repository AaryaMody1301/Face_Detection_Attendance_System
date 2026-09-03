# Privacy and repository data policy

This application processes face images and attendance records. Those files are runtime data, not source code, and must remain outside Git.

## Never commit

- captured or enrolled face images;
- trained recognition artifacts derived from enrolled faces;
- attendance exports or backups;
- student rosters containing real identities;
- runtime SQLite databases;
- generated credential or user-state files.

The repository `.gitignore` and `scripts/check_repository_hygiene.py` enforce these rules for future commits.

## Existing Git history

Removing files in a new commit removes them from the current branch tip, but does **not** erase copies from older commits. If any previously committed images, rosters, attendance records, databases, or credentials contain real data, repository history should be rewritten with a history-cleaning tool such as `git filter-repo`, followed by rotating any exposed credentials and coordinating a forced update with all collaborators.

History rewriting is intentionally not performed automatically by the application or CI because it is destructive and affects every clone and open branch.
