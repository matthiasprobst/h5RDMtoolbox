db = h5tbx.FileDB(collection=[hdf_filename, hdf_filenames])

search_result = db.find_one({'$basename': 'grp1'})