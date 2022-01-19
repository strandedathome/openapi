import os
import json
from typing import List, Optional, Dict
import logzero
from logzero import logger
from fastapi import FastAPI, APIRouter, Request, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from aiocache import caches, cached
from pydantic import BaseModel
from rolls.rpc.full_node_rpc_client import FullNodeRpcClient
from rolls.util.bech32m import encode_puzzle_hash, decode_puzzle_hash as inner_decode_puzzle_hash
from rolls.types.spend_bundle import SpendBundle
from rolls.types.blockchain_format.program import Program
import config as settings

caches.set_config(settings.CACHE_CONFIG)


app = FastAPI()

cwd = os.path.dirname(__file__)

log_dir = os.path.join(cwd, "logs")

if not os.path.exists(log_dir):
    os.mkdir(log_dir)

logzero.logfile(os.path.join(log_dir, "api.log"))


async def get_full_node_client() -> FullNodeRpcClient:
    config = settings.ROLLS_CONFIG
    full_node_client = await FullNodeRpcClient.create(config['self_hostname'], config['full_node']['rpc_port'], settings.ROLLS_ROOT_PATH, settings.ROLLS_CONFIG)
    return full_node_client


@app.on_event("startup")
async def startup():
    app.state.client = await get_full_node_client()
    # check full node connect
    await app.state.client.get_blockchain_state()


@app.on_event("shutdown")
async def shutdown():
    app.state.client.close()
    await app.state.client.await_closed()


def to_hex(data: bytes):
    return data.hex()


def decode_puzzle_hash(address):
    try:
        return inner_decode_puzzle_hash(address)
    except ValueError:
        raise HTTPException(400, "Invalid Address")

def coin_to_json(coin):
    return {
        'parent_coin_info':  to_hex(coin.parent_coin_info),
        'puzzle_hash': to_hex(coin.puzzle_hash),
        'amount': str(coin.amount)
    }


router = APIRouter()


class UTXO(BaseModel):
    parent_coin_info: str
    puzzle_hash: str
    amount: str


@router.get("/utxos", response_model=List[UTXO])
@cached(ttl=10, key_builder=lambda *args, **kwargs: f"utxos:{kwargs['address']}", alias='default')
async def get_utxos(address: str, request: Request):
    # todo: use blocke indexer and supoort unconfirmed param
    pzh = decode_puzzle_hash(address)
    full_node_client = request.app.state.client
    coin_records = await full_node_client.get_coin_records_by_puzzle_hash(puzzle_hash=pzh, include_spent_coins=True)
    data = []

    for row in coin_records:
        if row.spent:
            continue
        data.append(coin_to_json(row.coin))
    return data


@router.post("/sendtx")
async def create_transaction(request: Request, item = Body({})):
    spb = SpendBundle.from_json_dict(item['spend_bundle'])
    full_node_client = request.app.state.client
    
    try:
        resp = await full_node_client.push_tx(spb)
    except ValueError as e:
        logger.warning("sendtx: %s, error: %r", spb, e)
        raise HTTPException(400, str(e))
 
    return {
        'status': resp['status'],
        'id': spb.name().hex()
    }


class PecanRollsRpcParams(BaseModel):
    method: str
    params: Optional[Dict] = None


@router.post('/rolls_rpc')
async def full_node_rpc(request: Request, item: PecanRollsRpcParams):
    # todo: limit method and add cache
    full_node_client = request.app.state.client
    async with full_node_client.session.post(full_node_client.url + item.method, json=item.params, ssl_context=full_node_client.ssl_context) as response:
        res_json = await response.json()
        return res_json


async def get_user_balance(puzzle_hash: bytes, request: Request):
    full_node_client = request.app.state.client
    coin_records = await full_node_client.get_coin_records_by_puzzle_hash(puzzle_hash=puzzle_hash, include_spent_coins=True)
    amount = sum([c.coin.amount for c in coin_records if c.spent == 0])
    return amount


@router.get('/balance')
@cached(ttl=10, key_builder=lambda *args, **kwargs: f"balance:{kwargs['address']}", alias='default')
async def query_balance(address, request: Request):
    # todo: use blocke indexer and supoort unconfirmed param
    puzzle_hash = decode_puzzle_hash(address)
    amount = await get_user_balance(puzzle_hash, request)
    data = {
        'amount': amount
    }
    return data


DEFAULT_TOKEN_LIST = [
    {
        'chain': 'rolls',
        'id': 'rolls',
        'name': 'ROLLS',
        'symbol': 'ROLLS',
        'decimals': 12,
        'logo_url': 'https://pecanrolls.net/images/rolls-spinning-512.gif',
        'is_verified': True,
        'is_core': True,
    },
]


@router.get('/tokens')
async def list_tokens():
    return DEFAULT_TOKEN_LIST


app.include_router(router, prefix="/v1")
