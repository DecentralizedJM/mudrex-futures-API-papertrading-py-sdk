"""
Wallet API Module
=================

Endpoints for spot wallet balance and fund transfers.
"""

from typing import TYPE_CHECKING

from mudrex.api.base import BaseAPI
from mudrex.models import WalletBalance, FuturesBalance, TransferResult, WalletType

if TYPE_CHECKING:
    from mudrex.client import MudrexClient


class WalletAPI(BaseAPI):
    """
    Wallet management endpoints.
    
    Use these methods to:
    - Check spot wallet balance
    - Check futures wallet balance
    - Transfer funds between spot and futures wallets
    
    Example:
        >>> client = MudrexClient(api_secret="...")
        >>> 
        >>> # Check spot balance
        >>> balance = client.wallet.get_spot_balance()
        >>> print(f"Available: ${balance.available}")
        >>> 
        >>> # Transfer to futures
        >>> result = client.wallet.transfer_to_futures("100")
        >>> print(f"Transferred: ${result.amount}")
    """
    
    def get_spot_balance(self) -> WalletBalance:
        """
        Get spot wallet balance.
        
        Returns your total balance, available balance, rewards,
        and withdrawable amount.
        
        Returns:
            WalletBalance: Spot wallet balance details
            
        Example:
            >>> balance = client.wallet.get_spot_balance()
            >>> print(f"Total: ${balance.total}")
            >>> print(f"Available: ${balance.available}")
            >>> print(f"Withdrawable: ${balance.withdrawable}")
        """
        response = self._post("/wallet/funds")
        return WalletBalance.from_dict(response.get("data", response))
    
    def get_futures_balance(self) -> FuturesBalance:
        """
        Get futures wallet balance.
        
        Returns your futures balance, available transfer amount,
        unrealized PnL, and margin used.
        
        Returns:
            FuturesBalance: Futures wallet balance details
            
        Example:
            >>> balance = client.wallet.get_futures_balance()
            >>> print(f"Balance: ${balance.balance}")
            >>> print(f"Unrealized PnL: ${balance.unrealized_pnl}")
        """
        response = self._get("/futures/funds")
        return FuturesBalance.from_dict(response.get("data", response))
    
    def transfer_to_futures(self, amount: str) -> TransferResult:
        """
        Transfer funds from spot to futures wallet.
        
        Args:
            amount: Amount to transfer (as string for precision)
            
        Returns:
            TransferResult: Transfer confirmation details
            
        Example:
            >>> result = client.wallet.transfer_to_futures("50.00")
            >>> if result.success:
            ...     print(f"Transferred ${result.amount} to futures")
        """
        return self._transfer(
            from_wallet=WalletType.SPOT,
            to_wallet=WalletType.FUTURES,
            amount=amount,
        )
    
    def transfer_to_spot(self, amount: str) -> TransferResult:
        """
        Transfer funds from futures to spot wallet.
        
        Args:
            amount: Amount to transfer (as string for precision)
            
        Returns:
            TransferResult: Transfer confirmation details
            
        Example:
            >>> result = client.wallet.transfer_to_spot("25.00")
            >>> if result.success:
            ...     print(f"Transferred ${result.amount} to spot")
        """
        return self._transfer(
            from_wallet=WalletType.FUTURES,
            to_wallet=WalletType.SPOT,
            amount=amount,
        )
    
    def _transfer(
        self,
        from_wallet: WalletType,
        to_wallet: WalletType,
        amount: str,
    ) -> TransferResult:
        """
        Internal method to transfer funds between wallets.
        
        Args:
            from_wallet: Source wallet type
            to_wallet: Destination wallet type
            amount: Amount to transfer
            
        Returns:
            TransferResult: Transfer confirmation
        """
        response = self._post("/wallet/futures/transfer", {
            "from_wallet_type": from_wallet.value,
            "to_wallet_type": to_wallet.value,
            "amount": amount,
        })
        
        # Build result from response
        result_data = response.get("data", {})
        result_data["success"] = response.get("success", True)
        result_data["from_wallet_type"] = from_wallet.value
        result_data["to_wallet_type"] = to_wallet.value
        result_data["amount"] = amount
        
        return TransferResult.from_dict(result_data)
