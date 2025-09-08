async def delete_file(self, **kwargs) -> str:
    """Delete a file."""
    try:
        file_path = kwargs.get("file_path")
        
        async with self.agtsdbx_client as client:
            result = await client.delete_file(file_path)
            
            # INDENTED - Now INSIDE the async with block
            if result.get("success"):
                return f"Successfully deleted: {file_path}"
            else:
                return f"Failed to delete file: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"Error deleting file: {str(e)}"