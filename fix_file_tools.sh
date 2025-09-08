#!/bin/bash
# Fix the indentation issue in file_tools.py

sed -i '
/async def delete_file/,/except Exception as e:/ {
    /result = await client.delete_file/a\
                \
                if result.get("success"):\
                    return f"Successfully deleted: {file_path}"\
                else:\
                    return f"Failed to delete file: {result.get('"'"'error'"'"', '"'"'Unknown error'"'"')}"
    /^        if result.get/,/^                return f"Failed to delete/d
}
' frontend/src/tools/file_tools.py

echo "Fixed indentation in delete_file method"
