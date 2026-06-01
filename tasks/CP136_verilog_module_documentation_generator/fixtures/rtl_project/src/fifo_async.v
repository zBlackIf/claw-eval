// =============================================================================
// Module: fifo_async
// Description: Asynchronous FIFO with Gray code pointer synchronization
// Author: Design Team
// =============================================================================

module fifo_async #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 4,
    parameter DEPTH      = (1 << ADDR_WIDTH)
)(
    // Write domain
    input  wire                  wr_clk,
    input  wire                  wr_rst_n,
    input  wire                  wr_en,
    input  wire [DATA_WIDTH-1:0] wr_data,
    output reg                   wr_full,
    output wire [ADDR_WIDTH:0]   wr_count,

    // Read domain
    input  wire                  rd_clk,
    input  wire                  rd_rst_n,
    input  wire                  rd_en,
    output reg  [DATA_WIDTH-1:0] rd_data,
    output reg                   rd_empty,
    output wire [ADDR_WIDTH:0]   rd_count,

    // Status flags
    output wire                  almost_full,
    output wire                  almost_empty,
    output wire                  overflow,
    output wire                  underflow
);

    // =========================================================================
    // Internal signals
    // =========================================================================

    // Memory array
    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    // Binary pointers
    reg [ADDR_WIDTH:0] wr_ptr_bin;
    reg [ADDR_WIDTH:0] rd_ptr_bin;

    // Gray code pointers
    reg [ADDR_WIDTH:0] wr_ptr_gray;
    reg [ADDR_WIDTH:0] rd_ptr_gray;

    // Synchronized gray pointers (cross-domain)
    reg [ADDR_WIDTH:0] wr_ptr_gray_sync1, wr_ptr_gray_sync2;
    reg [ADDR_WIDTH:0] rd_ptr_gray_sync1, rd_ptr_gray_sync2;

    // Next pointer values
    wire [ADDR_WIDTH:0] wr_ptr_bin_next;
    wire [ADDR_WIDTH:0] rd_ptr_bin_next;
    wire [ADDR_WIDTH:0] wr_ptr_gray_next;
    wire [ADDR_WIDTH:0] rd_ptr_gray_next;

    // Converted pointers for comparison
    wire [ADDR_WIDTH:0] rd_ptr_bin_from_gray;

    // Error flags
    reg overflow_r, underflow_r;

    // =========================================================================
    // Gray code conversion functions
    // =========================================================================

    function [ADDR_WIDTH:0] bin2gray;
        input [ADDR_WIDTH:0] bin;
        begin
            bin2gray = bin ^ (bin >> 1);
        end
    endfunction

    function [ADDR_WIDTH:0] gray2bin;
        input [ADDR_WIDTH:0] gray;
        integer i;
        begin
            gray2bin[ADDR_WIDTH] = gray[ADDR_WIDTH];
            for (i = ADDR_WIDTH - 1; i >= 0; i = i - 1)
                gray2bin[i] = gray2bin[i+1] ^ gray[i];
        end
    endfunction

    // =========================================================================
    // Write domain logic
    // =========================================================================

    assign wr_ptr_bin_next  = wr_ptr_bin + (wr_en & ~wr_full);
    assign wr_ptr_gray_next = bin2gray(wr_ptr_bin_next);

    always @(posedge wr_clk or negedge wr_rst_n) begin
        if (!wr_rst_n) begin
            wr_ptr_bin  <= {(ADDR_WIDTH+1){1'b0}};
            wr_ptr_gray <= {(ADDR_WIDTH+1){1'b0}};
        end else begin
            wr_ptr_bin  <= wr_ptr_bin_next;
            wr_ptr_gray <= wr_ptr_gray_next;
        end
    end

    // Write data to memory
    always @(posedge wr_clk) begin
        if (wr_en && !wr_full)
            mem[wr_ptr_bin[ADDR_WIDTH-1:0]] <= wr_data;
    end

    // Synchronize read pointer to write domain (2-stage FF)
    always @(posedge wr_clk or negedge wr_rst_n) begin
        if (!wr_rst_n) begin
            rd_ptr_gray_sync1 <= {(ADDR_WIDTH+1){1'b0}};
            rd_ptr_gray_sync2 <= {(ADDR_WIDTH+1){1'b0}};
        end else begin
            rd_ptr_gray_sync1 <= rd_ptr_gray;
            rd_ptr_gray_sync2 <= rd_ptr_gray_sync1;
        end
    end

    // Full flag generation
    always @(posedge wr_clk or negedge wr_rst_n) begin
        if (!wr_rst_n)
            wr_full <= 1'b0;
        else
            wr_full <= (wr_ptr_gray_next == {~rd_ptr_gray_sync2[ADDR_WIDTH:ADDR_WIDTH-1],
                                              rd_ptr_gray_sync2[ADDR_WIDTH-2:0]});
    end

    // =========================================================================
    // Read domain logic
    // =========================================================================

    assign rd_ptr_bin_next  = rd_ptr_bin + (rd_en & ~rd_empty);
    assign rd_ptr_gray_next = bin2gray(rd_ptr_bin_next);

    always @(posedge rd_clk or negedge rd_rst_n) begin
        if (!rd_rst_n) begin
            rd_ptr_bin  <= {(ADDR_WIDTH+1){1'b0}};
            rd_ptr_gray <= {(ADDR_WIDTH+1){1'b0}};
        end else begin
            rd_ptr_bin  <= rd_ptr_bin_next;
            rd_ptr_gray <= rd_ptr_gray_next;
        end
    end

    // Read data from memory
    always @(posedge rd_clk) begin
        if (rd_en && !rd_empty)
            rd_data <= mem[rd_ptr_bin[ADDR_WIDTH-1:0]];
    end

    // Synchronize write pointer to read domain (2-stage FF)
    always @(posedge rd_clk or negedge rd_rst_n) begin
        if (!rd_rst_n) begin
            wr_ptr_gray_sync1 <= {(ADDR_WIDTH+1){1'b0}};
            wr_ptr_gray_sync2 <= {(ADDR_WIDTH+1){1'b0}};
        end else begin
            wr_ptr_gray_sync1 <= wr_ptr_gray;
            wr_ptr_gray_sync2 <= wr_ptr_gray_sync1;
        end
    end

    // Empty flag generation
    always @(posedge rd_clk or negedge rd_rst_n) begin
        if (!rd_rst_n)
            rd_empty <= 1'b1;
        else
            rd_empty <= (rd_ptr_gray_next == wr_ptr_gray_sync2);
    end

    // =========================================================================
    // Status and count logic
    // =========================================================================

    assign rd_ptr_bin_from_gray = gray2bin(rd_ptr_gray_sync2);
    assign wr_count = wr_ptr_bin - rd_ptr_bin_from_gray;

    wire [ADDR_WIDTH:0] wr_ptr_bin_from_gray;
    assign wr_ptr_bin_from_gray = gray2bin(wr_ptr_gray_sync2);
    assign rd_count = wr_ptr_bin_from_gray - rd_ptr_bin;

    // Almost full: when count >= DEPTH - 2
    assign almost_full  = (wr_count >= (DEPTH - 2));
    // Almost empty: when count <= 1
    assign almost_empty = (rd_count <= 1);

    // Overflow detection
    always @(posedge wr_clk or negedge wr_rst_n) begin
        if (!wr_rst_n)
            overflow_r <= 1'b0;
        else
            overflow_r <= wr_en & wr_full;
    end
    assign overflow = overflow_r;

    // Underflow detection
    always @(posedge rd_clk or negedge rd_rst_n) begin
        if (!rd_rst_n)
            underflow_r <= 1'b0;
        else
            underflow_r <= rd_en & rd_empty;
    end
    assign underflow = underflow_r;

endmodule
