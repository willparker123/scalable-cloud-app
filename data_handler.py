from concurrent.futures import thread
from msilib.schema import File
from operator import indexOf
import pandas as pd
import numpy as np
import math
import time
import os
import errno
import sys
import win32com #for metadata class
import win32com.client 

def path_exists_or_creatable(path: str) -> bool:
    '''
    `True` if the passed path is a valid path for the current OS;
    `False` otherwise.
    '''
    try:
        if not isinstance(path, str) or not path:
            return False
        _, path = os.path.splitdrive(path)
        root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
            if sys.platform == 'win32' else os.path.sep
        assert os.path.isdir(root_dirname)
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep
        for path_part in path.split(os.path.sep):
            try:
                os.lstat(root_dirname + path_part)
            except OSError as exc:
                if exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    except TypeError as exc:
        return False
    else:
        return True

def convert_str_to_date(date: str) -> pd.DataFrame:
    formatted_date = date
    return formatted_date

class Metadata():
    """
    Class for metadata of a file / record 
    [inspiration from: https://stackoverflow.com/questions/12521525/reading-metadata-with-python]

    Attributes 
    ----------
    name: str:
        Name of the file
    path: str:
        Path to the file
    size: int:
        Size of the file (in bytes)
    extension: str
        The file's extension without the period (".")
    dates: tuple(DATE, DATE)
        A tuple of ('date_modified', 'date_created')
    """
    def __init__(self, name: str, path: str, size: int, extension: str, dates: tuple) -> None:
        if not extension.startswith("."):
            raise ValueError("Error: 'extension' is not a valid extension")
        self.extension = extension.lower()
        if not path_exists_or_creatable(path):
            raise ValueError("Error: path does not exist or is an invalid path")
        self.path = path
        self.name = name
        if size < 0:
            raise ValueError("Error: file 'size' is < 0")
        self.size = size
        self.dates = dates

    def get_metadata_from_file(path: str):
        # Path shouldn't end with backslash, i.e. "E:\Images\Paris"
        # filename must include extension, i.e. "PID manual.pdf"
        # Returns dictionary containing all file metadata.
        if not path_exists_or_creatable(path):
            raise ValueError("Error: path does not exist or is an invalid path")
        head, tail = os.path.split(path)
        fn, ex = os.path.splitext(tail)
        if not ex.startswith("."):
            raise ValueError("Error: path does not have a valid extension")
        ex = ex.lower()
        sh = win32com.client.gencache.EnsureDispatch('Shell.Application', 0)
        ns = sh.NameSpace(head)
        metadata = ['name', 'size', 'type', 'date_modified', 'date_created']
        # Enumeration is necessary because ns.GetDetailsOf only accepts an integer as 2nd argument
        file_metadata = dict()
        file_metadata['name'] = fn
        file_metadata['size'] = os.path.getsize(path)
        file_metadata['type'] = ex
        file_metadata['date_modified'] = os.path.getmtime(path)
        file_metadata['date_created'] = os.path.getctime(path)
        return Metadata(name=fn, path=path, size=os.path.getsize(path), extension=ex, dates=(os.path.getmtime(path), os.path.getctime(path)))

class File_Obj():
    """
    Class for a file / record with metadata
    
    Parameters
    ----------
    filepath_i : str
        Filepath to read from
    filepath_o? : str
        Filepath for output
        -- Default is filepath_0 = filepath_i

    Attributes
    ----------
    filesize: int
        Filesize in Bytes
    metadata: metadata
        Metadata for the file
    filepath_i : str
        Filepath to read from
    filepath_o : str
        Filepath for output
        -- Default is filepath_0 = filepath_i
    filename: str
        Filename with extension
    data: pd.DataFrame
        Data that the file contains

    Methods
    ----------
    read_data(filepath?: str) -> pd.DataFrame:
        Reads the data from the file into a pd.DataFrame
        --Reads from filepath if supplied
    update_data(data?: pd.DataFrame):
        Updates the data file and self.data to the file contents or 'data' if supplied
    process_data(data? pd.DataFrame) -> pd.DataFrame:
        Processes self.data or 'data' if supplied
    """
    def __init__(self, *args, **kwargs) -> None:
        # IF CLASS EXTENDS: super(class, self).__init__(*args, **kwargs)
        if not ('filepath_i' in kwargs):
            raise ValueError("Error: 'no filepath_i' supplied to file_obj class")
        self.filepath_i = kwargs.get("filepath_i")
        if not path_exists_or_creatable(self.filepath_i):
            raise ValueError("Error: self.filepath_i does not exist or is an invalid path")
        self.filepath_o = self.filepath_i
        if ('filepath_o' in kwargs):
            self.filepath_o = kwargs.get("filepath_o")
            if not path_exists_or_creatable(self.filepath_o):
                raise ValueError("Error: self.filepath_o does not exist or is an invalid path")
        try:
            self.metadata = Metadata.get_metadata_from_file(self.filepath_i)
        except:
            self.metadata = None
        self.filesize = os.path.getsize(self.filepath_i)
        assert (self.filesize == self.metadata.size)
        assert (self.filepath_i == self.metadata.path)
        self.data = self.read_data()
        self.filename = os.path.os.path.split(self.filepath_i)[1]
        
    def read_data(self, filepath: str=None) -> pd.DataFrame:
        """Reads the data from the file into a pd.DataFrame
            --Reads from filepath if supplied"""
        p = self.filepath_i
        if filepath is not None:
            p = filepath
        head, ext = os.path.os.path.splitext(p)
        data_temp = pd.DataFrame()
        if ext == ".csv":
            data_temp = pd.read_csv(p)
        elif ext == ".dat":
            data_temp = np.genfromtxt(p,
                     skip_header=0,
                     skip_footer=0,
                     names=True,
                     dtype=None,
                     delimiter=' ', encoding="utf-8")
        else:
            raise ValueError(f"Error: cannot read file with extension '{ext}'")
        data = data_temp
        return data
    
    def update_data(self, data: pd.DataFrame=None):
        """Updates the data file and self.data to the file contents or 'data' if supplied"""
        #update data file to filecontents
        d = self.read_data()
        if data is not None:
            d = data
        #write data file to d
        self.data = d

    def process_data(self, func: lambda x: x, data: pd.DataFrame=None) -> pd.DataFrame:
        """Processes self.data or 'data' if supplied"""
        """ ***PLACEHOLDER FOR PROCESSING A FILE*** """
        d = self.data
        if data is not None:
            d = data
        newdata = func(d)
        self.update_data(data=newdata)
        return newdata
        
nThreads: int = 4
folderPathData = "data"
fileExtension = ".dat"



def distribute(*values):
    low = min(values)
    high = max(values)
    if high - low <= 1:
        #print('values already balanced')
        return list(values)
    s = sum(values)
    n = len(values)
    avg = s // n
    result = [avg] * n
    for i in range(s % n):
        result[i] += 1
    return result
#print(f"{distribute(*[1, 2, 0, 0])}")
# [1, 1, 1, 0]
def get_diff_matrix(lists):
    #*** SMALLEST SUM OF DIFFERENCE BETWEEN N LISTS (len(lists)) ***
    #lists = [[]]
    sums = list(map(lambda l: sum(l), lists))
    diffmatrix = []
    for a in range(len(sums)):
        diffs = [None]*len(sums)
        diffmatrix.append(diffs)
    for a in range(len(sums)):
        for b in range(len(sums)):
            if a == b:
                continue
            if diffmatrix[b][a] is not None:
                diffmatrix[a][b] = diffmatrix[b][a]
            xs = lists[a]
            ys = lists[b]
            diffmatrix[a][b] = sum(abs(x - y) for x, y in zip(sorted(xs), sorted(ys)))
    #[[None, 97924, 202900, 275212], 
    #[97924, None, 104976, 177288], 
    #[202900, 104976, None, 72312],
    #[275212, 177288, 72312, None]]
    #
    #    00 01 02 03 10 11 12 13 20 21 22 23
    # 0 1 2 3
    #0X Y 
    #1Y X Y
    #2  Y X Y
    #3    Y X
    return diffmatrix
#print(f"{distribute_lists(*[[1, 2], [3, 4], [0], [0]])}")
# [[1], [2], [3], [4]]
#print(f"{distribute_lists(*[[1, 2], [3, 4], [4, 4], [5, 2]])}")
# [[1], [2], [3], [4]]
def distribute_schedule(zipped_schedule: list, key_v=1, schedulelen: int=4):
    #zipped_schedule = [(proc[], filesize[]), (proc[], filesize[]), (proc[], filesize[]), (proc, filesize[])]
    threadno = len(zipped_schedule)
    key_tosort = lambda x: x[key_v]
    key_procs = lambda x: x[1-key_v]
    data_tosort = []
    for n in range(threadno):
        data_tosort.append([key_tosort(x) for x in zipped_schedule[n]])
    
    diffmatrix = get_diff_matrix(data_tosort)
    largestn = math.comb(threadno, 2)
    diffmatrix = np.array(diffmatrix)
    smallestx = 1000000000000000
    for j in range(len(data_tosort)):
        if min(data_tosort[j]) < smallestx:
            smallestx = min(data_tosort[j])
    for c in range(threadno):
        diffmatrix[c][:] = [x if not (x == None or x < smallestx) else 0 for x in diffmatrix[c]]
    # *** GET LARGEST threadnoCHOOSE2 (4C2=6 if threadno=4) VALUES FROM DIFFMATRIX ***
    diffmatrix_inds = [(e//threadno, e-(e//threadno * threadno)) for e in diffmatrix.flatten().argsort()[::-1][:largestn]]
    print(f"Smallest Filesize: {smallestx}, Difference Matrix Indicies (order of importance): {diffmatrix_inds}, Difference Matrix: {diffmatrix}")
    
    for n in range(threadno):
        temp_tosort = [key_tosort(x) for x in zipped_schedule[n]]
        temp_procs = [key_procs(x) for x in zipped_schedule[n]]
        if key_v == 0:
            tempzip = zip(temp_tosort, temp_procs)
        elif key_v == 1:
            tempzip = zip(temp_procs, temp_tosort)
        else:
            raise ValueError("Error: 'key_v' must be 0 or 1")
        zipped_schedule[n] = tempzip
    
    final_procs = []
    for n in range(threadno):
        final_procs.append(list(map(key_procs, zipped_schedule[n])))
    return final_procs

def get_priority(proc: tuple, procId: int, maxProcs: int):
    return (maxProcs - procId) % maxProcs

# *** SCHEDULING THE PROCS ***
def create_procs(inds: list):
    procs = []
    for j in inds:
        fn = file_list[j]
        fp = f'{folderPathData}/{fn}{ext}'
        procs.append(File_Obj(filepath_i=fp))
    return procs

def get_proc_schedule(nprocs: int, nthreads: int, procs_all: list, procs_done: list, schedulelen: int=4):
    procs_canbe = list(filter(lambda p: not p in procs_done, procs_all))
    inds__ = procs_canbe[0:schedulelen]
    if nthreads < 1:
        return inds__
    else:
        return np.array_split(inds__, nthreads)

def get_proc_schedule_filesize(nprocs: int, nthreads: int, procs_all: list, procs_done: list, filesizes_all: list, schedulelen: int=4):
    zipped_all = zip(procs_all, filesizes_all)
    procs_canbe = list(filter(lambda p: not p in procs_done, procs_all))
    filesizes_canbe = list(map(lambda o: o[1], list(filter(lambda z: z[0] in procs_canbe, zipped_all))))
    #if not (len(filesizes) == schedulelen):
    #    raise ValueError("Error: 'schedulelen' must be the same as the length of the supplied 'filesizes'")
    zipped = zip(procs_canbe, filesizes_canbe)
    zipped_after_sort_largest_filesize = list(reversed(sorted(zipped, key=lambda x: x[1])))
    inds__ = list(map(lambda x: x[0], zipped_after_sort_largest_filesize[0:nthreads]))
    if nthreads < 1:
        return inds__
    else:
        return np.array_split(inds__, nthreads)

def get_proc_schedule_filesize_batch(nprocs: int, nthreads: int, procs_all: list, procs_done: list, filesizes_all: list, schedulelen: int=4):
    zipped_all = zip(procs_all, filesizes_all)
    procs_canbe = list(filter(lambda p: not p in procs_done, procs_all))
    filesizes_canbe = list(map(lambda o: o[1], list(filter(lambda z: z[0] in procs_canbe, zipped_all))))
    #if not (len(filesizes) == schedulelen):
    #    raise ValueError("Error: 'schedulelen' must be the same as the length of the supplied 'filesizes'")
    zipped = zip(procs_canbe, filesizes_canbe)
    zipped_after_sort_largest_filesize = list(reversed(sorted(zipped, key=lambda x: x[1])))
    inds__ = list(map(lambda x: x[0], zipped_after_sort_largest_filesize))
    filesizes__ = list(map(lambda x: x[1], zipped_after_sort_largest_filesize))
    schedule = []
    schedule_fs = []
    zipped_schedule = []
    for N in range(nthreads):
        schedule.append([])
        schedule_fs.append([])
    rem = len(inds__) % nthreads
    fac = len(inds__) // nthreads
    d = 0
    while d < len(inds__):
        for N in range(nthreads):
            schedule[N].append(inds__[d+N])
            schedule_fs[N].append(filesizes__[d+N])
        d += nthreads
    d -= nthreads
    for N in range(rem):
        schedule[N].append(inds__[d+N])
        schedule_fs[N].append(filesizes__[d+N])
    for N in range(nthreads):
        zipped_schedule.append(zip(schedule[N], schedule_fs[N])) #zipped (proc, filesize)
    
    if nthreads < 1:
        return inds__
    else:
        final_schedule = distribute_schedule(zipped_schedule, key_v=1, schedulelen=schedulelen)
        return final_schedule

if __name__ == "__main__":
    # Load data from .dat file; can be replaced with call to generate_data_abinito.py
    
    ext = fileExtension
    file_list = list(map(lambda y: y[:-4], list(filter(lambda x: x.endswith(ext), list(next(os.walk(folderPathData))[2])))))
    
    n_procs = len(file_list)
    print(f"Number of files to be processed: {n_procs}")

    # *** CREATE ALL PROCS ***
    procs_all = create_procs(range(n_procs))
    procs_done = []
    inds_all = range(n_procs)
    filesizes_all = list(map(lambda p: p.filesize, procs_all))
    scheduled_procs_all = get_proc_schedule_filesize(n_procs, 0, procs_all, procs_done, filesizes_all, n_procs)
    scheduled_procs_all_split = get_proc_schedule_filesize(n_procs, nThreads, procs_all, procs_done, filesizes_all, n_procs)

    counter = 0
    while len(procs_done) < len(procs_all):
        procs = []
        for n in range(nThreads):
            procs.append([])
        # *** SCHEDULER - IN ORDER ***
        #for n in range(nThreads):
        #    j = n+counter
        #    fn = file_list[j]
        #    fp = f'{folderPathData}/{fn}{ext}'
        #    procs.append(File_Obj(filepath_i=fp))
        # **** ABOVE SCHEDULER IS EQUIVALENT TO THIS ****
        proc_inds = list(map(lambda x: x+counter, range(nThreads)))
        # **** ALSO EQUIVALENT TO THIS ****
        scheduled_procs = get_proc_schedule(n_procs, nThreads, procs_all, procs_done)
        
        # *** SCHEDULER USING FILESIZE LOCALLY - CAN ALSO USE schedule_inds ***
        
        scheduled_procs = get_proc_schedule_filesize_batch(n_procs, nThreads, procs_all, procs_done, filesizes_all, nThreads)
        
        # SCHEDULE nThreads PROCS: 2D array of length nThreadsa
        procs = scheduled_procs_all_split

        # *** PROCESSING THE PROCS ***
        c = 0
        for N in range(nThreads):
            for i, proc in enumerate(procs[N]):
                print(f"* Processing File {procs_all.index(proc)}:  Number {c+i+1}/{n_procs} - FilePath: {proc.filename} *")
                proc.process_data(func=lambda x: x)
                data_from_file = proc.read_data()
                print(f"FileName: {proc.filename}, Data: {data_from_file}")
                
                procs_done.append(proc)
            c += len(procs[N])
    
    print(f"*** Processing Complete: {n_procs} files processed ***")