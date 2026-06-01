// =============================================================================
// Module: uart_tx
// Description: UART Transmitter with configurable baud rate
// =============================================================================

module uart_tx #(
    parameter CLK_FREQ  = 50_000_000,
    parameter BAUD_RATE = 115200
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] tx_data,
    input  wire       tx_start,
    output reg        tx_out,
    output reg        tx_busy,
    output reg        tx_done
);

    localparam CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

    // State encoding
    localparam S_IDLE  = 3'b000;
    localparam S_START = 3'b001;
    localparam S_DATA  = 3'b010;
    localparam S_STOP  = 3'b011;
    localparam S_DONE  = 3'b100;

    reg [2:0]  state;
    reg [15:0] clk_count;
    reg [2:0]  bit_index;
    reg [7:0]  tx_shift;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= S_IDLE;
            tx_out    <= 1'b1;
            tx_busy   <= 1'b0;
            tx_done   <= 1'b0;
            clk_count <= 16'd0;
            bit_index <= 3'd0;
            tx_shift  <= 8'd0;
        end else begin
            tx_done <= 1'b0;
            case (state)
                S_IDLE: begin
                    tx_out <= 1'b1;
                    if (tx_start) begin
                        state     <= S_START;
                        tx_shift  <= tx_data;
                        tx_busy   <= 1'b1;
                        clk_count <= 16'd0;
                    end
                end

                S_START: begin
                    tx_out <= 1'b0;  // Start bit
                    if (clk_count == CLKS_PER_BIT - 1) begin
                        state     <= S_DATA;
                        clk_count <= 16'd0;
                        bit_index <= 3'd0;
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end

                S_DATA: begin
                    tx_out <= tx_shift[bit_index];
                    if (clk_count == CLKS_PER_BIT - 1) begin
                        clk_count <= 16'd0;
                        if (bit_index == 3'd7) begin
                            state <= S_STOP;
                        end else begin
                            bit_index <= bit_index + 1'b1;
                        end
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end

                S_STOP: begin
                    tx_out <= 1'b1;  // Stop bit
                    if (clk_count == CLKS_PER_BIT - 1) begin
                        state <= S_DONE;
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end

                S_DONE: begin
                    tx_busy <= 1'b0;
                    tx_done <= 1'b1;
                    state   <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
