"""
Chart generator utility for creating interactive plots and static images of market data.
Supports both HTML output for web display and PNG images for AI pattern analysis.
"""
import io
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.logger.logger import Logger


class ChartGenerator:
    """Generates interactive charts and static images for market data with OHLCV and RSI."""
    
    def __init__(self, logger: Optional[Logger] = None, config: Optional[Any] = None, formatter: Optional[Callable] = None):
        """Initialize the chart generator.
        
        Args:
            logger: Optional logger instance for debugging
            config: Optional config instance to avoid circular imports
            formatter: Optional formatting function for price formatting (e.g., fmt from format_utils)
        """
        self.logger = logger
        self.config = config
        self.formatter = formatter or self._default_formatter
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
        # AI chart candle limit from config
        self.ai_candle_limit = config.AI_CHART_CANDLE_LIMIT if config is not None else 200
        
    def _default_formatter(self, val, precision=8):
        """Default formatter for price values when no formatter is provided."""
        if isinstance(val, (int, float)) and not np.isnan(val):
            if abs(val) < 0.00001:
                return f"{val:.8f}"
            elif abs(val) < 0.01:
                return f"{val:.6f}"
            elif abs(val) < 10:
                return f"{val:.4f}"
            else:
                return f"{val:.2f}"
        return "N/A"
        
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
                    if len(values) > limit_candles:
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
            decreasing_line_color=colors['candle_down'],
            increasing_line_width=3 if for_ai else 1,  # Thicker lines for AI visibility
            decreasing_line_width=3 if for_ai else 1,
            line=dict(width=2 if for_ai else 1)  # Wick line width
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

        # Configure X-axes with improved spacing for AI charts
        if for_ai:
            tick_format = '%m/%d'  # Simplified format for better spacing
            tick_angle = 0  # No rotation for clarity
            nticks = 6  # Fewer ticks to prevent overlap
        else:
            tick_format = '%b %d, %H:%M'
            tick_angle = 0
            nticks = None
        
        fig.update_xaxes(
            showgrid=True,
            gridwidth=2 if for_ai else 1,
            gridcolor=colors['grid'],
            zeroline=False,
            tickformat=tick_format,
            tickangle=tick_angle,
            showticklabels=True,
            type='date',
            nticks=nticks,
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
        height: int = 600,  # Reduced from 600 for better aspect ratio
        width: int = 1600,   # Reduced from 1000 for better file size
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
            fig = self._create_simple_candlestick_chart(ohlcv, pair_symbol, timeframe, height, width)
            
            # Generate the image with reduced scale for better file size while maintaining readability
            img_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
            
            if save_to_disk:
                # Save to disk for testing purposes
                if output_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    chart_type = "simple" if simple_mode else "full"
                    # Use config path if available
                    base_path = self.config.DEBUG_CHART_SAVE_PATH if self.config else "test_images"
                    
                    filename = f"{pair_symbol.replace('/', '')}_{timeframe}_{chart_type}_AI_analysis_{timestamp}.png"
                    output_path = os.path.join(os.getcwd(), base_path, filename)
                

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(img_bytes)
                
                if self.logger:
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
        # Determine limit: parameter > instance ai_candle_limit
        chosen_limit = int(self.ai_candle_limit)
        if chosen_limit and len(ohlcv) > chosen_limit:
            ohlcv = ohlcv[-chosen_limit:]

        timestamps = pd.to_datetime(ohlcv[:, 0], unit='ms')
        timestamps_py = timestamps.to_pydatetime().tolist()
        opens = ohlcv[:, 1].astype(float)
        highs = ohlcv[:, 2].astype(float)
        lows = ohlcv[:, 3].astype(float)
        closes = ohlcv[:, 4].astype(float)
        
        # Create single subplot for price only
        fig = go.Figure()
        
        # Add candlestick chart with AI-optimized colors and visibility
        candle = go.Candlestick(
            x=timestamps_py,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="Price",
            increasing_line_color=self.ai_colors['candle_up'],
            decreasing_line_color=self.ai_colors['candle_down'],
            increasing_line_width=1.2,  # thinner body edges
            decreasing_line_width=1.2,
            line=dict(width=0.8)  # thinner wick for clearer peaks
        )
        fig.add_trace(candle)
        
    # Layout for simple chart optimized for AI with price formatting
        current_price = float(closes[-1])  # Get current price for title
        current_price_formatted = self.formatter(current_price)

        # Determine dynamic decimal places for y-axis tick formatting
        abs_price = abs(current_price) if current_price != 0 else 0.0
        if abs_price == 0:
            decimals = 2
        elif abs_price < 1e-6:
            decimals = 9
        elif abs_price < 1e-5:
            decimals = 8
        elif abs_price < 1e-4:
            decimals = 7
        elif abs_price < 1e-3:
            decimals = 6
        elif abs_price < 1e-2:
            decimals = 5
        elif abs_price < 1e-1:
            decimals = 4
        elif abs_price < 1:
            decimals = 4
        elif abs_price < 10:
            decimals = 3
        else:
            decimals = 2
        y_tickformat = f".{decimals}f"
        
        fig.update_layout(
            title=f"{pair_symbol} Price Pattern - {timeframe} (Last {chosen_limit} Candles) - Current: {current_price_formatted}",
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
        
        # Simple Y-axis configuration - denser grid
        fig.update_yaxes(
            title_text="Price",
            showgrid=True,
            gridwidth=0.8,  # Thinner lines for denser appearance
            gridcolor=self.ai_colors['grid'],
            zeroline=False,
            tickformat=y_tickformat,
            exponentformat='none',
            showexponent='none',
            # Add more price levels for denser grid
            nticks=15,  # More horizontal grid lines
            # Add minor ticks for even denser grid
            minor=dict(
                showgrid=True,
                gridwidth=0.5,
                gridcolor='rgba(64, 64, 64, 0.3)'  # Lighter color for minor grid
            )
        )
        
        # Simple x-axis configuration for AI analysis - denser grid
        fig.update_xaxes(
            title_text="Date/Time",
            showgrid=True,
            gridwidth=0.8,  # Thinner lines for denser appearance
            gridcolor=self.ai_colors['grid'],
            zeroline=False,
            tickformat='%m/%d %H:%M',  # Simple, readable format
            tickangle=-45,  # Angle labels for readability
            nticks=20,  # More ticks for denser grid (increased from 12)
            type='date',
            tickfont=dict(size=9),  # Smaller font to fit more labels
            automargin=True,
            showline=True,
            linewidth=1,
            linecolor=self.ai_colors['grid'],
            # Add minor ticks for even denser grid
            minor=dict(
                showgrid=True,
                gridwidth=0.5,
                gridcolor='rgba(64, 64, 64, 0.3)'  # Lighter color for minor grid
            )
        )

        # Replace the OHLC header with a short explanation for AI
        info_text = (
            "Chart contains OHLC candles; thinner wicks mark highs/lows. "
        )
        fig.add_annotation(
            xref='paper', yref='paper', x=0.01, y=0.99,
            xanchor='left', yanchor='top',
            text=info_text,
            showarrow=False,
            font=dict(size=11, family='Arial, sans-serif', color=self.ai_colors['text']),
            bgcolor='rgba(0,0,0,0.3)',
            bordercolor=self.ai_colors['grid'],
            borderwidth=1,
            align='left'
        )

        # Optional: keep a subtle current price reference line (helps AI with context)
        try:
            fig.add_hline(y=float(closes[-1]), line=dict(color='#555555', width=1, dash='dot'))
        except Exception:
            pass

        # --- Highest/Lowest point annotations ---
        idx_high = int(np.argmax(highs))
        idx_low = int(np.argmin(lows))
        fig.add_annotation(
            x=timestamps_py[idx_high], y=float(highs[idx_high]),
            text=f"Highest (high ohlcv): {self.formatter(float(highs[idx_high]))}",
            showarrow=True, arrowhead=2, arrowsize=0.9, arrowwidth=1.0,
            ax=0, ay=-30,
            font=dict(size=12, color=self.ai_colors['text']),
            bgcolor='rgba(0,0,0,0.5)', bordercolor=self.ai_colors['grid'], borderwidth=1
        )
        fig.add_annotation(
            x=timestamps_py[idx_low], y=float(lows[idx_low]),
            text=f"Lowest (low ohlcv): {self.formatter(float(lows[idx_low]))}",
            showarrow=True, arrowhead=2, arrowsize=0.9, arrowwidth=1.0,
            ax=0, ay=30,
            font=dict(size=12, color=self.ai_colors['text']),
            bgcolor='rgba(0,0,0,0.5)', bordercolor=self.ai_colors['grid'], borderwidth=1
        )
        
        return fig