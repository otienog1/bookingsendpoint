# Instance Directory

This directory contains instance-specific files and data that should not be committed to version control.

## Structure

```
instance/
├── copyparty-files/     # Document storage for Copyparty server
│   └── (uploaded files are stored here)
└── README.md           # This file
```

## copyparty-files/

This directory is used by the Copyparty server to store uploaded documents.

- **Purpose**: File storage for booking documents
- **Access**: Files are served through the Copyparty web server
- **Security**: Files are only accessible through authenticated share links
- **Organization**: Files are named with booking ID and timestamp for uniqueness

## Important Notes

- This directory is automatically created when the application starts
- The entire `instance/` directory should be added to `.gitignore`
- In production, ensure this directory has proper backup procedures
- File permissions should be configured to allow the application to read/write