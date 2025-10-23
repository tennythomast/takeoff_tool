# Temporary File Storage

This directory is used for temporary storage of uploaded files in development mode.

## Structure

Files are organized in subdirectories following this pattern:
```
temp_storage/
  ├── {organization_id}/
  │   └── {workspace_id}/
  │       └── {filename}
  └── ...
```

## Important Notes

1. This is intended for **development purposes only**
2. In production, files should be stored in a proper storage backend (S3, GCS, etc.)
3. Files in this directory are served via Django's static file serving in development
4. All files in this directory (except this README and .gitignore) are ignored by Git

## Access URLs

Files can be accessed at: `/temp-storage/{organization_id}/{workspace_id}/{filename}`
