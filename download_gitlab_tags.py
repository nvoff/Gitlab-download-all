import os
import requests
import subprocess
from tqdm import tqdm
from urllib.parse import quote

GITLAB_HOST = "gitlab.example.ru"
GROUP = "GROUP_NAME"
TOKEN = "YOU_TOKEN_HERE"
API_BASE = f"https://{GITLAB_HOST}/api/v4"
HEADERS = {"PRIVATE-TOKEN": TOKEN}
CLONE_DIR = "./"

def get_group_id(group_path):
    url = f"{API_BASE}/groups/{quote(group_path, safe='')}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()["id"]

def get_all_projects(group_id):
    page = 1
    all_projects = []

    while True:
        url = f"{API_BASE}/groups/{group_id}/projects?include_subgroups=true&per_page=100&page={page}"
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        projects = r.json()
        if not projects:
            break
        all_projects.extend(projects)
        page += 1

    return all_projects

def clone_or_pull(path, repo_url):
    if os.path.isdir(os.path.join(path, ".git")):
        print(f"🔁 Обновляю {path}")
        subprocess.run(["git", "-C", path, "pull"], check=True)
        subprocess.run(["git", "-C", path, "fetch", "--all"], check=True)
    elif os.path.isdir(path):
        print(f"⚠️ Пропускаю (не git): {path}")
    else:
        print(f"⬇️ Клонирую {path}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        subprocess.run(["git", "clone", repo_url, path], check=True)
        subprocess.run(["git", "-C", path, "fetch", "--all"], check=True)

    result = subprocess.run(["git", "-C", path, "branch", "-r"], capture_output=True, text=True, check=True)
    remote_branches = [line.strip() for line in result.stdout.splitlines() if "->" not in line]

    local_branches_result = subprocess.run(["git", "-C", path, "branch"], capture_output=True, text=True, check=True)
    local_branches = {line.strip().lstrip("* ") for line in local_branches_result.stdout.splitlines()}

    for remote_branch in remote_branches:
        if remote_branch.startswith("origin/"):
            branch_name = remote_branch.replace("origin/", "")
            if branch_name not in local_branches:
                subprocess.run(["git", "-C", path, "branch", branch_name, remote_branch], check=True)


def main():
    print(f"📡 Получаю ID группы '{GROUP}'...")
    group_id = get_group_id(GROUP)
    print(f"✅ ID группы: {group_id}")

    print("📥 Получаю список проектов (включая подгруппы)...")
    projects = get_all_projects(group_id)
    print(f"📦 Найдено проектов: {len(projects)}")

    for project in tqdm(projects, desc="Обработка проектов"):
        path = project["path_with_namespace"].lower()  # или без lower()
        repo_url = project["ssh_url_to_repo"]
        full_path = os.path.join(CLONE_DIR, path)
        try:
            clone_or_pull(full_path, repo_url)
        except subprocess.CalledProcessError:
            print(f"❌ Ошибка при работе с {path}")

if __name__ == "__main__":
    main()