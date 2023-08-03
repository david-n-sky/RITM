import os

source_dir = 'C:\\Users\\gelya\\PycharmProjects\\updater'

destination_dir = 'C:\\Users\\gelya\\PycharmProjects'

for root, dirs, files in os.walk(source_dir):
    for file in files:
        local_path = os.path.join(root, file)
        lp = local_path.replace(source_dir, '')
        remote_path = os.path.join(destination_dir)
        print(remote_path + lp)

