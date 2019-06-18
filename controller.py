import os, json
from shutil import copyfile

filename = "chapter2.txt"

def load_data_from_file(path=None):
    with open(path if path else filename, 'r') as f:
        data = f.read()
    return data

def find_qty_of_replication():
    files = os.listdir("data")
    first_shard = list(filter(lambda x: x.startswith("0"),files))
    list1 = [int(x.split("-")[1][:-4]) for x in first_shard if "-" in x]
    if list1:
        return max(list1)
    else:
        return 0

class ShardHandler(object):
    """
    Take any text file and shard it into X number of files with
    Y number of replications.
    """
    def __init__(self):
        self.mapping = self.load_map()

    mapfile = "mapping.json"

    def write_map(self):
        """Write the current 'database' mapping to file."""
        with open(self.mapfile, 'w') as m:
            json.dump(self.mapping, m, indent=2)

    def load_map(self):
        """Load the 'database' mapping from file."""
        if not os.path.exists(self.mapfile):
            return dict()
        with open(self.mapfile, 'r') as m:
            return json.load(m)

    def delete_shard_data(self,*argv):
        for num in argv:
            path_ = f"data/{num}.txt"
            print(path_)
            if os.path.exists(path_):
                print("TRUE")
                os.remove(path_)
                self.mapping.pop(str(num))

    def build_shards(self, count, data=None):
        """Initialize our miniature databases from a clean mapfile. Cannot
        be called if there is an existing mapping -- must use add_shard() or
        remove_shard()."""
        if self.mapping != {}:
            return "Cannot build shard setup -- sharding already exists."

        spliced_data = self._generate_sharded_data(count, data)

        for num, d in enumerate(spliced_data):
            self._write_shard(num, d)

        self.write_map()

    def _write_shard(self, num, data):
        """Write an individual database shard to disk and add it to the
        mapping."""
        if not os.path.exists("data"):
            os.mkdir("data")
        with open(f"data/{num}.txt", 'w') as s:
            s.write(data)

        self.mapping.update(
            {
                str(num): {
                    'start': num * len(data),
                    'end': (num + 1) * len(data)
                }
            }
        )

    def _generate_sharded_data(self, count, data):
        """Split the data into as many pieces as needed."""
        splicenum, rem = divmod(len(data), count)

        result = [data[splicenum * z:splicenum * (z + 1)] for z in range(count)]
        # take care of any odd characters
        if rem > 0:
            result[-1] += data[-rem:]

        return result

    def load_data_from_shards(self):
        """Grab all the shards, pull all the data, and then concatenate it."""
        result = list()

        for db in self.mapping.keys():
            with open(f'data/{db}.txt', 'r') as f:
                result.append(f.read())
        return ''.join(result)

    def add_shard(self):
        """Add a new shard to the existing pool and rebalance the data."""
        self.mapping = self.load_map()
        data = self.load_data_from_shards()
        # why 2? Because we have to compensate for zero indexing
        keys = [int(z) for z in list(self.mapping.keys())]
        keys.sort()
        new_shard_num = str(max(keys) + 2)
        spliced_data = self._generate_sharded_data(int(new_shard_num), data)

        for num, d in enumerate(spliced_data):
            self._write_shard(num, d)

        self.write_map()
        self.sync_replication()

    def remove_shard(self):
        """Loads the data from all shards, removes the extra 'database' file,
        and writes the new number of shards to disk.
        """
        self.mapping = self.load_map()
        data = self.load_data_from_shards()
        current_number_of_shards = len(self.mapping.keys())
        new_shard_num = current_number_of_shards - 1 if current_number_of_shards > 1 else 1
        spliced_data = self._generate_sharded_data(new_shard_num, data)
        self.delete_shard_data(new_shard_num)
        for num, d in enumerate(spliced_data):
            self._write_shard(num, d)
        self.write_map()
        self.sync_replication()

    def add_replication(self):
        """Add a level of replication so that each shard has a backup. Label
        them with the following format:

        1.txt (shard 1, primary)
        1-1.txt (shard 1, replication 1)
        1-2.txt (shard 1, replication 2)
        2.txt (shard 2, primary)
        2-1.txt (shard 2, replication 1)
        ...etc.

        By default, there is no replication -- add_replication should be able
        to detect how many levels there are and appropriately add the next
        level.
        """
    
        qty_of_rep = find_qty_of_replication()
        for key in self.mapping.keys():
            src = f"data/{key}.txt"
            dsc = f"data/{key}-{str(qty_of_rep + 1)}.txt"
            copyfile(src, dsc)
            

    def remove_replication(self):
        """Remove the highest replication level.

        If there are only primary files left, remove_replication should raise
        an exception stating that there is nothing left to remove.

        For example:

        1.txt (shard 1, primary)
        1-1.txt (shard 1, replication 1)
        1-2.txt (shard 1, replication 2)
        2.txt (shard 2, primary)
        etc...

        to:

        1.txt (shard 1, primary)
        1-1.txt (shard 1, replication 1)
        2.txt (shard 2, primary)
        etc...
        """
        qty_of_rep = find_qty_of_replication()
        if qty_of_rep == 0:
            raise Exception("There is no replication to remove")
        for key in self.mapping.keys():
            os.remove(f"data/{key}-{str(qty_of_rep)}.txt")

    def sync_replication(self):
        """Verify that all replications are equal to their primaries and that
         any missing primaries are appropriately recreated from their
         replications."""
        qty_of_rep = find_qty_of_replication()
        files = os.listdir("data")
        map_keys_set = set(self.mapping.keys())
        for f in files:
            if "-" in f:
                file_name_split = f.split("-")
            else:
                file_name_split = f
            if file_name_split[0] not in map_keys_set:
                os.remove(f"data/{f}")
        for key in map_keys_set:
            src = f"data/{key}.txt"
            for i in range(qty_of_rep):
                dsc = f"data/{key}-{str(i+1)}.txt"
                copyfile(src,dsc)

    def get_shard_data(self, shardnum=None):
        """Return information about a shard from the mapfile."""
        if not shardnum:
            return self.get_all_shard_data()
        data = self.mapping.get(shardnum)
        if not data:
            return f"Invalid shard ID. Valid shard IDs: {self.mapping.keys()}"
        return f"Shard {shardnum}: {data}"

    def get_all_shard_data(self):
        """A helper function to view the mapping data."""
        return self.mapping


s = ShardHandler()

s.build_shards(5, load_data_from_file())

print(s.mapping.keys())

# s.add_shard()
s.remove_shard()


print(s.mapping.keys())

# s.add_replication()
# s.add_replication()
s.remove_replication()
