"""
Chart generator utility for creating interactive plots and static images of market data.
Supports both HTML output for web display and PNG images for AI pattern analysis.
"""
import io
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.logger.logger import Logger


class ChartGenerator:
    """Generates interactive charts and static images for market data with OHLCV and RSI."""
    
    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the chart generator.
        
        Args:
            logger: Optional logger instance for debugging
        """
        self.logger = logger
        self.default_colors = {
            'background': '#1a1a1a',
            'grid': '#333333',
            'text': '#e0e0e0',
            'candle_up': '#26a69a',
            'candle_down': '#ef5350',
            'volume': '#3370d4',
            'rsi': '#e6c700'
        }
        
        # AI-optimized colors for better pattern recognition
        self.ai_colors = {
            'background': '#000000',  # Pure black for maximum contrast
            'grid': '#404040',        # Lighter grid for visibility
            'text': '#ffffff',        # Pure white text
            'candle_up': '#00ff00',   # Bright green for bullish candles
            'candle_down': '#ff0000', # Bright red for bearish candles
            'volume': '#0080ff',      # Bright blue for volume
            'rsi': '#ffff00'          # Bright yellow for RSI
        }
        
    def _create_base_chart(
        self,
        ohlcv: np.ndarray,
        technical_history: Optional[Dict[str, np.ndarray]] = None,
        pair_symbol: str = "",
        timeframe: str = "1h",
        height: int = 800,
        width: int = None,
        for_ai: bool = False,
        limit_candles: int = None
    ) -> go.Figure:
        """Create the base chart figure that can be used for both HTML and image output.
        
        Args:
            ohlcv: OHLCV data array
            technical_history: Optional technical indicators data
            pair_symbol: Trading pair symbol
            timeframe: Chart timeframe
            height: Chart height
            width: Chart width
            for_ai: If True, optimize colors and layout for AI analysis
            limit_candles: Optional limit on number of candles (e.g., 200 for AI analysis)
            
        Returns:
            Plotly figure object
        """
        # Limit candles if specified (for AI analysis)
        if limit_candles and len(ohlcv) > limit_candles:
            ohlcv = ohlcv[-limit_candles:]
            if technical_history:
                # Also limit technical indicators to match
                for key, values in technical_history.items():
                    if isinstance(values, np.ndarray) and len(values) > limit_candles:
                        technical_history[key] = values[-limit_candles:]
        
        # Choose color scheme based on usage
        colors = self.ai_colors if for_ai else self.default_colors

        # Convert timestamps to Python datetime for reliable Plotly date axes
        # Using Python datetime objects avoids axis type inference issues in static image export
        timestamps = pd.to_datetime(ohlcv[:, 0], unit='ms')
        timestamps_py = timestamps.to_pydatetime().tolist()
        
        # Determine if RSI data is available
        has_rsi = technical_history and 'rsi' in technical_history and len(technical_history['rsi']) == len(timestamps)

        # Create subplots: 3 rows if RSI, 2 rows if no RSI
        rows = 3 if has_rsi else 2
        if has_rsi:
            row_heights = [0.7, 0.15, 0.15]  # Price gets 70%, Volume 15%, RSI 15%
            specs = [
                [{"secondary_y": True}],   # Price row with secondary y-axis
                [{"secondary_y": False}],  # Volume row
                [{"secondary_y": False}]   # RSI row
            ]
        else:
            row_heights = [0.8, 0.2]  # Price gets 80%, Volume 20%
            specs = [
                [{"secondary_y": True}],   # Price row with secondary y-axis  
                [{"secondary_y": False}]   # Volume row
            ]

        fig = make_subplots(
            rows=rows, 
            cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.05,
            row_heights=row_heights,
            specs=specs
        )
        
        # --- Plot 1: Price Candlesticks ---
        candle = go.Candlestick(
            x=timestamps_py,
            open=ohlcv[:, 1],
            high=ohlcv[:, 2],
            low=ohlcv[:, 3],
            close=ohlcv[:, 4],
            name="Price",
            increasing_line_color=colors['candle_up'],
            decreasing_line_color=colors['candle_down']
        )
        fig.add_trace(candle, row=1, col=1, secondary_y=True)
        
        # --- Plot 2: Volume ---
        volume = go.Bar(
            x=timestamps_py,
            y=ohlcv[:, 5],
            name="Volume",
            marker_color=colors['volume'],
            opacity=0.7 if for_ai else 0.6,  # Higher opacity for AI readability
        )
        fig.add_trace(volume, row=2, col=1)
        
        # --- Plot 3: RSI (if available) ---
        if has_rsi:
            rsi_values = technical_history['rsi']
            
            # Add RSI line in the third row
            fig.add_trace(go.Scatter(
                x=timestamps_py,
                y=rsi_values,
                name="RSI (14)",
                line=dict(color=colors['rsi'], width=2 if for_ai else 1.5)  # Thicker line for AI
            ), row=3, col=1)
            
            # Add RSI Overbought/Oversold lines
            oversold_color = 'rgba(0, 255, 0, 0.8)' if for_ai else 'rgba(38, 166, 154, 0.7)'
            overbought_color = 'rgba(255, 0, 0, 0.8)' if for_ai else 'rgba(239, 83, 80, 0.7)'
            
            for level, color, dash in [(70, overbought_color, 'dash'), (30, oversold_color, 'dash')]:
                fig.add_trace(go.Scatter(
                    x=[timestamps_py[0], timestamps_py[-1]],
                    y=[level, level],
                    mode='lines',
                    line=dict(color=color, width=2 if for_ai else 1, dash=dash),
                    showlegend=False,
                    hoverinfo='skip'
                ), row=3, col=1)

        # --- Layout Updates ---
        title_suffix = f" (Last {limit_candles} Candles)" if limit_candles else ""
        title_prefix = "Pattern Analysis" if for_ai else "Market Analysis"
        
        fig.update_layout(
            title=f"{pair_symbol} {title_prefix} - {timeframe}{title_suffix}",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=height,
            width=width,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="left",
                x=0
            ),
            font=dict(
                family="Arial, sans-serif", 
                size=14 if for_ai else 11,  # Larger font for AI readability
                color=colors['text']
            ),
            paper_bgcolor=colors['background'],
            plot_bgcolor=colors['background'],
            margin=dict(l=60 if for_ai else 40, r=60 if for_ai else 40, t=80, b=60 if for_ai else 40),
        )
        
        if not for_ai:
            # Add interactive features for HTML charts
            fig.update_layout(
                dragmode='zoom',
                hovermode='x unified',
                autosize=True
            )
        
        # --- Axis Configuration ---
        
        # Configure Primary Y-axis (Row 1, Left side) - Hidden
        fig.update_yaxes(
            showgrid=False,
            showticklabels=False,
            visible=False,
            row=1, col=1, 
            secondary_y=False
        )
        
        # Configure Price axis (Secondary Y-axis, Row 1, Right side)
        fig.update_yaxes(
            title_text="Price", 
            showgrid=True, 
            gridwidth=2 if for_ai else 1,  # Thicker grid for AI
            gridcolor=colors['grid'], 
            zeroline=False,
            side="right",
            row=1, col=1, 
            secondary_y=True
        )
        
        # Configure Volume axis (Row 2)
        fig.update_yaxes(
            title_text="Volume", 
            showgrid=True,
            gridwidth=2 if for_ai else 1,
            gridcolor=colors['grid'],
            zeroline=False,
            row=2, col=1
        )

        # Configure X-axes
        tick_format = '%m/%d %H:%M' if for_ai else '%b %d, %H:%M'
        tick_angle = 45 if for_ai else 0
        
        fig.update_xaxes(
            showgrid=True,
            gridwidth=2 if for_ai else 1,
            gridcolor=colors['grid'],
            zeroline=False,
            tickformat=tick_format,
            tickangle=tick_angle,
            showticklabels=True,
            type='date',
            row=rows, col=1  # Apply to the bottom-most x-axis
        )
        
        # Hide tick labels on the top x-axis if there are multiple rows
        if rows > 1:
            fig.update_xaxes(showticklabels=False, type='date', row=1, col=1)
            if rows > 2:
                fig.update_xaxes(showticklabels=False, type='date', row=2, col=1)
        
        # Configure RSI Y-axis (Row 3, if exists)
        if has_rsi:
            fig.update_yaxes(
                title_text="RSI",
                showgrid=True,
                gridwidth=2 if for_ai else 1,
                gridcolor=colors['grid'],
                zeroline=False,
                range=[0, 100],
                row=3, col=1
            )
        
        return fig
        
    def create_ohlcv_chart(
        self,
        ohlcv: np.ndarray,
        technical_history: Optional[Dict[str, np.ndarray]] = None,
        patterns: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        pair_symbol: str = "",
        timeframe: str = "1h",
        height: int = 800,
        width: int = None
    ) -> str:
        """Create an interactive HTML chart with OHLCV, Volume, and RSI."""
        fig = self._create_base_chart(
            ohlcv, technical_history, pair_symbol, timeframe, height, width, for_ai=False
        )
        
        # Generate a unique ID for this chart instance 
        chart_id = f"crypto_chart_{int(datetime.now().timestamp())}"
        
        # Configure for responsiveness and interaction
        config = {
            'responsive': True,
            'displayModeBar': True,
            'scrollZoom': True,  # Enable mouse wheel zoom
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],  # Remove selection tools
            'modeBarButtonsToAdd': ['resetScale2d'],  # Add reset scale button
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'{pair_symbol}_analysis',
                'scale': 2
            },
            'displaylogo': False  # Hide plotly logo for cleaner look
        }
        
        # Return the figure as HTML
        fig_html = fig.to_html(
            include_plotlyjs='cdn', 
            full_html=False, 
            div_id=chart_id,
            config=config
        )

        # Add a loading state for the chart
        chart_html = f"""
        <div id="{chart_id}-container" class="chart-loading-container">
            <div class="chart-loading" id="{chart_id}-loading">
                <div class="loading-spinner"></div>
                <p>Loading market data chart...</p>
            </div>
            {fig_html}
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const chartContainer = document.getElementById('{chart_id}-container');
                const loadingElement = document.getElementById('{chart_id}-loading');
                
                // Hide loading indicator when chart is ready
                if (chartContainer && loadingElement) {{
                    // Check if Plotly chart is ready
                    const checkPlotlyReady = setInterval(function() {{
                        if (document.querySelector('#{chart_id} .plot-container')) {{
                            loadingElement.style.display = 'none';
                            clearInterval(checkPlotlyReady);
                        }}
                    }}, 100);
                    
                    // Fallback timeout - hide loading after 5 seconds regardless
                    setTimeout(function() {{
                        if (loadingElement) loadingElement.style.display = 'none';
                    }}, 5000);
                }}
            }});
        </script>
        """
        return chart_html
    
    def create_chart_image(
        self,
        ohlcv: np.ndarray,
        technical_history: Optional[Dict[str, np.ndarray]] = None,
        pair_symbol: str = "",
        timeframe: str = "1h",
        height: int = 600,  # Reduced height for simple chart
        width: int = 1000,  # Reduced width for simple chart
        save_to_disk: bool = False,
        output_path: Optional[str] = None,
        simple_mode: bool = True  # Default to simple mode for AI analysis
    ) -> Union[io.BytesIO, str]:
        """Create a PNG chart image optimized for AI pattern analysis.
        
        Args:
            ohlcv: OHLCV data array with columns [timestamp, open, high, low, close, volume]
            technical_history: Optional technical indicators data
            pair_symbol: Trading pair symbol (e.g., "BTCUSDT")
            timeframe: Chart timeframe (e.g., "1h", "4h")
            height: Image height in pixels
            width: Image width in pixels
            save_to_disk: If True, saves image to disk for testing
            output_path: Optional custom output path for disk save
            simple_mode: If True, creates simplified chart with only price data (recommended for AI)
            
        Returns:
            BytesIO object containing PNG image data, or file path if saved to disk
        """
        try:
            if simple_mode:
                # Create simplified chart with only price data (recommended for AI pattern analysis)
                fig = self._create_simple_candlestick_chart(ohlcv, pair_symbol, timeframe, height, width)
            else:
                # Create full chart with volume and RSI, limited to 200 candles for AI analysis
                fig = self._create_base_chart(
                    ohlcv, technical_history, pair_symbol, timeframe, 
                    height, width, for_ai=True, limit_candles=200
                )
            
            # Generate the image
            img_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
            
            if save_to_disk:
                # Save to disk for testing purposes
                if output_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    chart_type = "simple" if simple_mode else "full"
                    # Use config path if available
                    try:
                        from src.utils.loader import config
                        base_path = config.DEBUG_CHART_SAVE_PATH
                    except:
                        base_path = "test_images"
                    
                    output_path = f"/workspaces/DiscordCryptoAnalyzer/{base_path}/{pair_symbol}_{timeframe}_{chart_type}_AI_analysis_{timestamp}.png"
                
                # Ensure directory exists
                import os
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(img_bytes)
                
                if self.logger:
                    self.logger.info(f"🖼️  DEBUG: Chart image saved for AI analysis: {output_path}")
                    self.logger.info(f"📊 Chart contains {len(ohlcv)} candles of {pair_symbol} {timeframe} data")
                    if len(ohlcv) > 0:
                        first_time = pd.to_datetime(ohlcv[0][0], unit='ms').strftime('%Y-%m-%d %H:%M')
                        last_time = pd.to_datetime(ohlcv[-1][0], unit='ms').strftime('%Y-%m-%d %H:%M')
                        current_price = ohlcv[-1][4]  # Close price of last candle
                        self.logger.info(f"📈 Data range: {first_time} to {last_time} | Current price: {current_price}")
                
                return output_path
            else:
                # Return BytesIO for memory efficiency
                img_buffer = io.BytesIO(img_bytes)
                img_buffer.seek(0)
                
                if self.logger:
                    self.logger.debug(f"Generated chart image for {pair_symbol} ({len(img_bytes)} bytes)")
                
                return img_buffer
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error generating chart image: {str(e)}")
            raise
    
    def _create_simple_candlestick_chart(
        self,
        ohlcv: np.ndarray,
        pair_symbol: str,
        timeframe: str,
        height: int,
        width: int
    ) -> go.Figure:
        """Create a simple candlestick chart focused on price action patterns.
        
        Args:
            ohlcv: OHLCV data array
            pair_symbol: Trading pair symbol
            timeframe: Chart timeframe
            height: Chart height
            width: Chart width
            
        Returns:
            Plotly figure object
        """
        # Limit to last 200 candles for AI analysis
        if len(ohlcv) > 200:
            ohlcv = ohlcv[-200:]

        timestamps = pd.to_datetime(ohlcv[:, 0], unit='ms')
        timestamps_py = timestamps.to_pydatetime().tolist()
        
        # Create single subplot for price only
        fig = go.Figure()
        
        # Add candlestick chart with AI-optimized colors
        candle = go.Candlestick(
            x=timestamps_py,
            open=ohlcv[:, 1],
            high=ohlcv[:, 2],
            low=ohlcv[:, 3],
            close=ohlcv[:, 4],
            name="Price",
            increasing_line_color=self.ai_colors['candle_up'],
            decreasing_line_color=self.ai_colors['candle_down']
        )
        fig.add_trace(candle)
        
        # Layout for simple chart optimized for AI
        fig.update_layout(
            title=f"{pair_symbol} Price Pattern - {timeframe} (Last 200 Candles)",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=height,
            width=width,
            font=dict(family="Arial, sans-serif", size=16, color=self.ai_colors['text']),
            paper_bgcolor=self.ai_colors['background'],
            plot_bgcolor=self.ai_colors['background'],
            margin=dict(l=60, r=60, t=80, b=60),
            showlegend=False  # Hide legend for cleaner look
        )
        
        # Configure axes with AI-optimized settings and readable timestamps
        fig.update_yaxes(
            title_text="Price",
            showgrid=True,
            gridwidth=2,
            gridcolor=self.ai_colors['grid'],
            zeroline=False
        )
        
        fig.update_xaxes(
            title_text="Date/Time",
            showgrid=True,
            gridwidth=2,
            gridcolor=self.ai_colors['grid'],
            zeroline=False,
            tickformat='%b %d, %H:%M',  # More readable format for AI: "Sep 18, 14:30"
            tickangle=45,
            nticks=8,  # Limit number of ticks for cleaner display
            type='date'
        )
        
        return fig