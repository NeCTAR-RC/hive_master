import os
from operator import itemgetter
from django.conf import settings
from django.shortcuts import render
from git import Repo, InvalidGitRepositoryError


def git_diverging_commits(repo):

    branch_sha = None
    upstream_sha = None
    try:
        branch = repo.active_branch
        branch_sha = branch.commit.hexsha
        upstream = branch.tracking_branch()
        upstream_sha = upstream.commit.hexsha
    except:
        return ([], None, branch_sha)
    commits = [c for c in
               repo.iter_commits("%s..%s" % (branch.commit.hexsha, upstream.commit.hexsha))]
    return (commits, upstream.commit.hexsha, branch.commit.hexsha)


def git_project(repo):
    try:
        remote = repo.remote()
    except:
        return None

    config = remote.config_reader.config
    try:
        url = config.get_value('remote "%s"' % remote.name, "url")
    except:
        return None

    if ":" in url:
        project = url.split(":")[1]
    else:
        return None
    if project.startswith("internal"):
        project = project + ".git"
    if not (project.startswith("internal") or
            project.startswith("NeCTAR-RC")):
        return None

    return project


def index(request):
    modules = []
    for module in os.listdir(settings.PUPPET_MODULES):
        path = os.path.join(settings.PUPPET_MODULES, module)
        try:
            repo = Repo(path)
        except InvalidGitRepositoryError:
            continue
        else:
            commits, upstream, branch = git_diverging_commits(repo)
            notes = []
            if not upstream:
                notes.append("No Upstream")
            if not branch:
                notes.append("No Branch")
            project = git_project(repo)
            if project:
                url = settings.GITWEB_BASE_URL + "?p=%s;a=summary" % project
                changes = settings.GITWEB_BASE_URL + "?p=%s;a=log;h=%s;hp=%s" % \
                          (project, upstream, branch)
            else:
                url = None
                changes = None
            modules.append({"commits_behind": len(commits),
                            "name": module,
                            "url": url,
                            "changes": changes,
                            "notes": ",".join(notes)})

    modules.sort(key=itemgetter("commits_behind"), reverse=True)
    context = {"modules": modules}

    return render(request, "index.html", context)
