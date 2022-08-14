import os

def get_filtered_df(df, column, value):
    df = df[df[column] == value]
    # Returns a df where all values of a certain column are a certain value
    return df

def create_new_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
        return True
    else:
        # Only create the folder if it is not already there
        return False
    
def fixpath(path):
    path = os.path.normpath(os.path.expanduser(path))
    if path.startswith("\\"): return "C:" + path
    return path