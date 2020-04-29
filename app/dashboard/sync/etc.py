from django.utils import timezone

import requests
from dashboard.sync.helpers import txn_already_used


def find_txn_on_etc_explorer(fulfillment, network='mainnet'):
    token_name = fulfillment.token_name
    if token_name != 'ETC':
        return None
    funderAddress = fulfillment.bounty.bounty_owner_address
    amount = fulfillment.payout_amount
    payeeAddress = fulfillment.fulfiller_address

    blockscout_url = f'https://blockscout.com/etc/{network}/api?module=account&action=txlist&address={funderAddress}'
    blockscout_response = requests.get(blockscout_url).json()
    if blockscout_response['message'] and blockscout_response['result']:
        for txn in blockscout_response['result']:
            if (
                txn['from'] == funderAddress.lower() and
                txn['to'] == payeeAddress.lower() and
                float(txn['value']) == float(amount) and
                not txn_already_used(txn['hash'], token_name)
            ):
                return txn
    return None


def get_etc_txn_status(txnid, network='mainnet'):
    if not txnid:
        return None

    blockscout_url = f'https://blockscout.com/etc/{network}/api?module=transaction&action=gettxinfo&txhash={txnid}'
    blockscout_response = requests.get(blockscout_url).json()

    if blockscout_response['status'] and blockscout_response['result']:

        response = {
            'blockNumber': int(blockscout_response['result']['blockNumber']),
            'confirmations': int(blockscout_response['result']['confirmations'])
        }

        if response['confirmations'] > 0:
            response['has_mined'] = True
        else:
            response['has_mined'] = False
        return response

    return None


def sync_etc_payout(fulfillment):
    if not fulfillment.payout_tx_id:
        txn = find_txn_on_etc_explorer(fulfillment)
        if txn:
            fulfillment.payout_tx_id = txn['hash']
    if fulfillment.payout_tx_id:
        txn_status = get_etc_txn_status(fulfillment.payout_tx_id)
        if txn_status and txn_status.get('has_mined'):
            fulfillment.payout_status = 'done'
            fulfillment.accepted_on = timezone.now()
            fulfillment.accepted = True
        fulfillment.save()
