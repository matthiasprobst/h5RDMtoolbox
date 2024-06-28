# Zenodo repository interface


## Provide Token(s)
In order to connect to Zenodo and interact with it, tokens for either the productive or
sandbox version must be provided. Either by providing a `zenodo.ini` file in the local
user directory (find it here: `h5rdmtoolbox.get_user_dir()`)

The file content should look like the following (displayed tokens are not real, replace them
with yours):

    [zenodo:sandbox]
    access_token = 123kwadhulahw7d8o141lhualwedhuao810g208
    [zenodo]
    access_token = jdalwd814o8h3aulih7o3r01h12ulieh218e7081

You may alo set them as environment variables. Please use `ZENODO_API_TOKEN` and `ZENODO_SANDBOX_API_TOKEN`,
respectively.

**Note**, that environment variables are checked first! If set the ini-file is not 
checked!