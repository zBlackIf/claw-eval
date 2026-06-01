// =============================================================================
// Module: spi_master
// Description: SPI Master controller with configurable clock polarity/phase
// =============================================================================

module spi_master #(
    parameter CLK_DIV_WIDTH = 8,
    parameter DATA_WIDTH    = 8
)(
    input  wire                  clk,
    input  wire                  rst_n,

    // Configuration
    input  wire [CLK_DIV_WIDTH-1:0] clk_div,  // SPI clock divider
    input  wire                  cpol,         // Clock polarity
    input  wire                  cpha,         // Clock phase

    // Control interface
    input  wire                  start,
    input  wire [DATA_WIDTH-1:0] tx_data,
    output reg  [DATA_WIDTH-1:0] rx_data,
    output reg                   busy,
    output reg                   done,

    // SPI signals
    output reg                   sclk,
    output reg                   mosi,
    input  wire                  miso,
    output reg                   cs_n
);

    // =========================================================================
    // State machine
    // =========================================================================

    localparam IDLE    = 3'b000;
    localparam SETUP   = 3'b001;
    localparam LEADING = 3'b010;
    localparam TRAILING= 3'b011;
    localparam DONE    = 3'b100;

    reg [2:0] state, next_state;

    // =========================================================================
    // Internal signals
    // =========================================================================

    reg [CLK_DIV_WIDTH-1:0] clk_cnt;
    reg [3:0]               bit_cnt;
    reg [DATA_WIDTH-1:0]    shift_reg;
    reg                     clk_edge;
    wire                    clk_half;

    assign clk_half = (clk_cnt == (clk_div >> 1));

    // =========================================================================
    // Clock divider
    // =========================================================================

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clk_cnt <= {CLK_DIV_WIDTH{1'b0}};
            clk_edge <= 1'b0;
        end else if (state == IDLE) begin
            clk_cnt <= {CLK_DIV_WIDTH{1'b0}};
            clk_edge <= 1'b0;
        end else begin
            if (clk_cnt >= clk_div - 1) begin
                clk_cnt <= {CLK_DIV_WIDTH{1'b0}};
                clk_edge <= 1'b1;
            end else begin
                clk_cnt <= clk_cnt + 1'b1;
                clk_edge <= (clk_cnt == ((clk_div >> 1) - 1));
            end
        end
    end

    // =========================================================================
    // State machine transitions
    // =========================================================================

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= IDLE;
        else
            state <= next_state;
    end

    always @(*) begin
        next_state = state;
        case (state)
            IDLE: begin
                if (start)
                    next_state = SETUP;
            end
            SETUP: begin
                next_state = LEADING;
            end
            LEADING: begin
                if (clk_edge)
                    next_state = TRAILING;
            end
            TRAILING: begin
                if (clk_edge) begin
                    if (bit_cnt == DATA_WIDTH - 1)
                        next_state = DONE;
                    else
                        next_state = LEADING;
                end
            end
            DONE: begin
                next_state = IDLE;
            end
            default: next_state = IDLE;
        endcase
    end

    // =========================================================================
    // Data shift register and bit counter
    // =========================================================================

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_reg <= {DATA_WIDTH{1'b0}};
            bit_cnt   <= 4'd0;
            rx_data   <= {DATA_WIDTH{1'b0}};
        end else begin
            case (state)
                IDLE: begin
                    bit_cnt <= 4'd0;
                    if (start)
                        shift_reg <= tx_data;
                end
                LEADING: begin
                    if (clk_edge) begin
                        if (cpha == 1'b0) begin
                            // Sample MISO on leading edge when CPHA=0
                            shift_reg <= {shift_reg[DATA_WIDTH-2:0], miso};
                        end
                    end
                end
                TRAILING: begin
                    if (clk_edge) begin
                        if (cpha == 1'b1) begin
                            // Sample MISO on trailing edge when CPHA=1
                            shift_reg <= {shift_reg[DATA_WIDTH-2:0], miso};
                        end
                        bit_cnt <= bit_cnt + 1'b1;
                    end
                end
                DONE: begin
                    rx_data <= shift_reg;
                end
            endcase
        end
    end

    // =========================================================================
    // Output generation
    // =========================================================================

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk <= 1'b0;
            mosi <= 1'b0;
            cs_n <= 1'b1;
            busy <= 1'b0;
            done <= 1'b0;
        end else begin
            done <= 1'b0;
            case (state)
                IDLE: begin
                    sclk <= cpol;
                    cs_n <= 1'b1;
                    busy <= 1'b0;
                    if (start) begin
                        cs_n <= 1'b0;
                        busy <= 1'b1;
                        mosi <= tx_data[DATA_WIDTH-1];
                    end
                end
                SETUP: begin
                    cs_n <= 1'b0;
                    mosi <= shift_reg[DATA_WIDTH-1];
                end
                LEADING: begin
                    if (clk_edge) begin
                        sclk <= ~sclk;
                        if (cpha == 1'b1)
                            mosi <= shift_reg[DATA_WIDTH-1];
                    end
                end
                TRAILING: begin
                    if (clk_edge) begin
                        sclk <= ~sclk;
                        if (cpha == 1'b0)
                            mosi <= shift_reg[DATA_WIDTH-1];
                    end
                end
                DONE: begin
                    sclk <= cpol;
                    cs_n <= 1'b1;
                    busy <= 1'b0;
                    done <= 1'b1;
                end
            endcase
        end
    end

endmodule
