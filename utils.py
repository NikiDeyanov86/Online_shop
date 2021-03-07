def validate_file_type(filename, allowed_types):
    '''
    Check if the file type is valid.
    Allowed types must be an array
    '''
    return filename.split(".")[-1] in allowed_types
