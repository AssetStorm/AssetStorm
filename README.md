# AssetStorm

![Logo by Albert Hulm](images/logo_500.png)

AssetStorm lets you save data with your preferred schemas in a 
PostgreSQL database. This can be used for publications like magazines
or websites but also for a lot of other things.

There is no frontend included with AssetStorm. It just exposes its 
[API](https://github.com/pinae/AssetStorm/blob/master/AssetStormAPI.yaml).

## Development setup
On Ubuntu install `postgresql` and `libpq-dev`.

After that create a virtual environment and install the requirements:
```shell script
python3 -m venv venv
source env/bin/activate
pip install -r requirements.txt
```

After that start the postgres server and create an account and a 
database for development:
```shell script
sudo systemctl start postgresql
sudo -u postgres psql postgres
```

```shell script
postgres=# \password postgres
Enter new password: 
Enter it again: 
postgres=# CREATE USER assetStorm;
CREATE ROLE
postgres=# CREATE DATABASE AssetStormDevelop OWNER assetStorm;
CREATE DATABASE
postgres=# \password assetStorm
Enter new password: 
Enter it again:
postgres=# ALTER USER assetstorm CREATEDB;
ALTER ROLE
```
