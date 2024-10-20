def save_data(users, path):
    file = open(path, "w")

    for user in users.keys():
        file.write(f"{user};{users[user][0]};{users[user][1]};{users[user][2]};\n")

    file.close()


def load_data(path):
    file = open(path, "r")
    users = {}

    for line in file.readlines():
        data = line.split(";")
        users[data[0]] = [data[1], data[2], data[3]]

    return users

