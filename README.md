# Social credit bot

## Way to clone
``` bash
git clone https://github.com/NRF24l01/social_credit_tgbot
cd social_credit_tgbot
```

## How to run
### Env config
Create .env with
```
TG_API=Your token
ADMIN_ID=Admin id, easely get from db(tg_id)
```

### Docker compose
#### Build
```bash
docker-compose build
```
#### Run
```bash
docker-compose up
```


### Docker
*Not good*
#### Build
```bash
docker build soc_credit_tgbot
```
#### Run
```bash
docker run --env-file .env --name soc_credit_tgbot soc_credit_tgbot 
```

*Profit!)*
