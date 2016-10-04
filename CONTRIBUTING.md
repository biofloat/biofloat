Instructions for contributing to the biofloat project
=====================================================

You are encouraged to contribute to biofloat!

You can learn how from this *free* series [How to Contribute to an Open Source Project on GitHub](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github).

### Setting up your development system
 
1. Use a computer with all the required Python modules or a computer with [Anaconda](https://www.continuum.io/)
   installed and clone the repository from https://github.com/biofloat/biofloat using either GitHub Desktop
   or on the command line, e.g.:

        cd ~/dev
        git clone https://github.com/biofloat/biofloat biofloatgit

2. Fork the repository after logging into GitHub by clicking on the Fork button at 
   https://github.com/biofloat/biofloat

3. Recommended: Generate SSH keys on your development system following the instructions at 
   https://help.github.com/articles/generating-ssh-keys/

4. Rename the existing `origin` remote to `upstream`, e.g.:

        cd ~/dev/biofloatgit
        git remote rename origin upstream

5. Assign `origin` remote to your forked repository:

        git remote add -f origin <your_github_clone_url>

   Replace \<your_github_clone_url\> with "Copy to clipboard" from GitHub web site

### Contributing follows a [typical GitHub workflow](https://guides.github.com/introduction/flow/):

1. cd into your working directory, e.g.:

        cd ~/dev/biofloatgit

2. Create a branch for the new feature: 

        git checkout master
        git checkout -b my_new_feature

3. Work on your feature; add and commit as you write code and test it. (Creating a new 
   branch is not strictly necessary, but it makes it easy to keep your commits separated
   from other development commits.

4. Before pushing the commits of your new feature please run `./test.sh` to make sure 
   the test coverage has not decreased.  Another way to state this is: Be sure to write 
   a test for your new feature in biofloat/biofloat/tests.

5. Push the new branch to your fork on GitHub:

        git push origin my_new_feature

6. Share your contribution with others by issuing a 
   [pull request](https://help.github.com/articles/using-pull-requests/): Click the 
   Pull Request button from your forked repository on GitHub

### Synchronizing with upstream

You should periodically pull changes to your workspace from the upstream remote.  These 
commands will synchronize your fork with upstream, including any local changes you have
committed:

    git checkout master
    git pull upstream master
    git push origin

After this you can use the GitHub web interface to visualize differences between your 
fork and upstream and submit a Pull Request.

If a lot of changes have happened upstream and you have local commits that you have 
not made public you may want to do a `rebase` instead of `merge`.  A `rebase` will 
replay your local changes on top of what is in upstream, e.g.:

    git fetch upstream
    git rebase upstream/master

or 
    `git rebase upstream/<branch_name>`, if a lot of upstream development is happening on another branch 

WARNING: This will rewrite commit history, so should only be done if your local commits 
have not been made public.

